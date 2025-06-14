"""
Setting up, running and shutting down the API and web-ui
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Iterable, Mapping
from os import urandom
from threading import Thread, Timer, current_thread
from typing import TYPE_CHECKING, Any

from backend.base.definitions import Constants, SocketEvent, StartType
from backend.base.files import folder_path
from backend.base.helpers import Singleton
from backend.base.logging import LOGGER, set_log_level, setup_logging
from backend.internals.db import (
    DBConnectionManager,
    close_db,
    set_db_location,
    setup_db_adapters_and_converters,
)
from backend.internals.settings import Settings
from flask import Flask, render_template, request
from flask_socketio import SocketIO
from waitress.server import create_server
from waitress.task import ThreadedTaskDispatcher as TTD
from werkzeug.middleware.dispatcher import DispatcherMiddleware

if TYPE_CHECKING:
    from backend.base.definitions import Download
    from backend.features.tasks import Task
    from flask.ctx import AppContext
    from waitress.server import BaseWSGIServer, MultiSocketServer


class ThreadedTaskDispatcher(TTD):
    def handler_thread(self, thread_no: int) -> None:
        # Most of this method's content is copied straight from waitress
        # except for the the part marked. The thread is considered to be
        # stopped when it's removed from self.threads, so we need to close
        # the database connection before it.
        while True:
            with self.lock:
                while not self.queue and self.stop_count == 0:
                    # Mark ourselves as idle before waiting to be
                    # woken up, then we will once again be active
                    self.active_count -= 1
                    self.queue_cv.wait()
                    self.active_count += 1

                if self.stop_count > 0:
                    self.active_count -= 1
                    self.stop_count -= 1

                    # =================
                    # Kapowarr part
                    thread_id = current_thread().native_id or -1
                    if (
                        thread_id in DBConnectionManager.instances
                        and not DBConnectionManager.instances[thread_id].closed
                    ):
                        DBConnectionManager.instances[thread_id].close()
                    # =================

                    self.threads.discard(thread_no)
                    self.thread_exit_cv.notify()
                    break

                task = self.queue.popleft()
            try:
                task.service()
            except BaseException:
                self.logger.exception("Exception when servicing %r", task)
        return

    def shutdown(self, cancel_pending: bool = True, timeout: int = 5) -> bool:
        print()
        LOGGER.info("Shutting down Kapowarr...")

        ws = WebSocket()
        if "/" in ws.server.manager.rooms:  # type: ignore
            for sid in tuple(ws.server.manager.rooms["/"][None]):  # type: ignore
                ws.server.disconnect(sid)  # type: ignore

        result = super().shutdown(cancel_pending, timeout)
        return result


def handle_start_type(start_type: StartType) -> None:
    """Do special actions needed based on the type of start.

    Args:
        start_type (StartType): The start type.
    """
    if start_type == StartType.RESTART_HOSTING_CHANGES:
        LOGGER.info("Starting timer for hosting changes")
        SERVER.revert_hosting_timer.start()

    return


def diffuse_timers() -> None:
    """Stop any timers running after doing a special restart."""
    if SERVER.revert_hosting_timer.is_alive():
        LOGGER.info("Timer for hosting changes diffused")
        SERVER.revert_hosting_timer.cancel()

    return


class Server(metaclass=Singleton):
    start_type: StartType | None
    api_prefix = "/api"

    def __init__(self) -> None:
        self.start_type = None
        self.url_base = ""

        self.revert_hosting_timer = Timer(
            Constants.HOSTING_TIMER_DURATION, self.restore_hosting_settings
        )
        self.revert_hosting_timer.name = "HostingHandler"

        return

    def create_app(self) -> None:
        """Creates an flask app instance that can be used to start a web server"""

        from frontend.api import api
        from frontend.ui import ui

        app = Flask(
            __name__,
            template_folder=folder_path("frontend", "templates"),
            static_folder=folder_path("frontend", "static"),
            static_url_path="/static",
        )
        app.config["SECRET_KEY"] = urandom(32)
        app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True
        app.config["JSON_SORT_KEYS"] = False

        ws = WebSocket()
        ws.init_app(
            app,
            path=f"{self.api_prefix}/socket.io",
            cors_allowed_origins="*",
            async_mode="threading",
        )

        # Add error handlers
        @app.errorhandler(404)
        def not_found(e: Any) -> str | tuple[dict[str, Collection[str]], int]:
            if request.path.startswith(self.api_prefix):
                return {"error": "NotFound", "result": {}}, 404
            return render_template("page_not_found.html")

        @app.errorhandler(400)
        def bad_request(e: Any) -> tuple[dict[str, Collection[str]], int]:
            return {"error": "BadRequest", "result": {}}, 400

        @app.errorhandler(405)
        def method_not_allowed(e: Any) -> tuple[dict[str, Collection[str]], int]:
            return {"error": "MethodNotAllowed", "result": {}}, 405

        @app.errorhandler(500)
        def internal_error(e: Any) -> tuple[dict[str, Collection[str]], int]:
            return {"error": "InternalError", "result": {}}, 500

        # Add endpoints
        app.register_blueprint(ui)
        app.register_blueprint(api, url_prefix=self.api_prefix)

        # Setup db handling
        app.teardown_appcontext(close_db)

        self.app = app
        return

    def set_url_base(self, url_base: str) -> None:
        """Change the URL base of the server.

        Args:
            url_base (str): The desired URL base to set it to.
        """
        self.app.config["APPLICATION_ROOT"] = url_base
        self.app.wsgi_app = DispatcherMiddleware(  # type: ignore
            Flask(__name__), {url_base: self.app.wsgi_app}
        )
        self.url_base = url_base
        return

    def __create_waitress_server(
        self, host: str, port: int
    ) -> MultiSocketServer | BaseWSGIServer:
        """From the `Flask` instance created in `self.create_app()`, create
        a waitress server instance.

        Args:
            host (str): Where to host the server on (e.g. `0.0.0.0`).
            port (int): The port to host the server on (e.g. `5656`).

        Returns:
            Union[MultiSocketServer, BaseWSGIServer]: The waitress server instance.
        """
        dispatcher = ThreadedTaskDispatcher()
        dispatcher.set_thread_count(Constants.HOSTING_THREADS)

        server = create_server(
            self.app,
            _dispatcher=dispatcher,
            host=host,
            port=port,
            threads=Constants.HOSTING_THREADS,
        )
        return server

    def run(self, host: str, port: int) -> None:
        """Start the webserver.

        Args:
            host (str): The host to bind to.
            port (int): The port to listen on.
        """
        self.server = self.__create_waitress_server(host, port)
        LOGGER.info(f"Kapowarr running on http://{host}:{port}{self.url_base}")
        self.server.run()

        return

    def __shutdown_thread_function(self) -> None:
        """Shutdown waitress server. Intended to be run in a thread."""
        if not hasattr(self, "server"):
            return

        self.server.task_dispatcher.shutdown()
        self.server.close()
        self.server._map.clear()  # type: ignore
        return

    def shutdown(self) -> None:
        """Stop the waitress server. Starts a thread that
        shuts down the server.
        """
        t = Timer(1.0, self.__shutdown_thread_function)
        t.name = "InternalStateHandler"
        t.start()
        return

    def restart(self, start_type: StartType = StartType.RESTART) -> None:
        """Same as `self.shutdown()`, but restart instead of shutting down.

        Args:
            start_type (StartType, optional): Why Kapowarr should
            restart_version (RestartVersion, optional): Why Kapowarr should
            restart.
                Defaults to StartType.RESTART.
        """
        self.start_type = start_type
        self.shutdown()
        return

    def restore_hosting_settings(self) -> None:
        "Restore the hosting settings from the backup, and restart."
        with self.app.app_context():
            settings = Settings()
            values = settings.get_settings()
            main_settings = {
                "host": values.backup_host,
                "port": values.backup_port,
                "url_base": values.backup_url_base,
            }
            settings.update(main_settings)
            self.restart()
        return

    def get_db_thread(
        self,
        target: Callable[..., object],
        name: str,
        args: Iterable[Any] = (),
        kwargs: Mapping[str, Any] = {},
    ) -> Thread:
        """Create a thread that runs under Flask app context.

        Args:
            target (Callable[..., object]): The function to run in the thread.
            name (str): The name of the thread.
            args (Iterable[Any], optional): The arguments to pass to the function.
                Defaults to ().
            kwargs (Mapping[str, Any], optional): The keyword arguments to pass
            to the function.
                Defaults to {}.

        Returns:
            Thread: The thread instance.
        """

        def db_thread(*args: Any, **kwargs: Any) -> None:
            with self.app.app_context():
                target(*args, **kwargs)

            thread_id = current_thread().native_id or -1
            if (
                thread_id in DBConnectionManager.instances
                and not DBConnectionManager.instances[thread_id].closed
            ):
                DBConnectionManager.instances[thread_id].close()

            return

        t = Thread(target=db_thread, name=name, args=args, kwargs=kwargs)
        return t


class WebSocket(SocketIO, metaclass=Singleton):
    def send_task_added(self, task: Task) -> None:
        """Send a message stating a task that has been added
        to the queue.

        Args:
            task (Task): The task that has been added.
        """
        self.emit(
            SocketEvent.TASK_ADDED.value,
            {
                "action": task.action,
                "volume_id": task.volume_id,
                "issue_id": task.issue_id,
            },
        )
        return

    def send_task_ended(self, task: Task) -> None:
        """Send a message stating a task that has been removed
        from the queue. Either because it's finished or canceled.

        Args:
            task (Task): The task that has been removed.
        """
        self.emit(
            SocketEvent.TASK_ENDED.value,
            {
                "action": task.action,
                "volume_id": task.volume_id,
                "issue_id": task.issue_id,
            },
        )
        return

    def update_task_status(
        self, task: Task | None = None, message: str | None = None
    ) -> None:
        """Send a message with the new task queue status. Supply either
        the task or the message.

        Args:
            task (Union[Task, None], optional): The task instance to send
            the status of.
                Defaults to None.

            message (Union[str, None], optional): The message to send.
                Defaults to None.
        """
        if task is not None:
            self.emit(SocketEvent.TASK_STATUS.value, {"message": task.message})

        elif message is not None:
            self.emit(SocketEvent.TASK_STATUS.value, {"message": message})

        return

    def send_queue_added(self, download: Download) -> None:
        """Send a message stating a download that has been added
        to the queue.

        Args:
            download (Download): The download that has been added.
        """
        self.emit(SocketEvent.QUEUE_ADDED.value, download.todict())
        return

    def send_queue_ended(self, download: Download) -> None:
        """Send a message stating a download that has been removed
        from the queue. Either because it's finished or canceled.

        Args:
            download (Download): The download that has been removed.
        """
        self.emit(SocketEvent.QUEUE_ENDED.value, {"id": download.id})
        return

    def update_queue_status(self, download: Download) -> None:
        """Send a message with the new download queue status.

        Args:
            download (Download): The download instance to send the status of.
        """
        self.emit(
            SocketEvent.QUEUE_STATUS.value,
            {
                "id": download.id,
                "status": download.state.value,
                "size": download.size,
                "speed": download.speed,
                "progress": download.progress,
            },
        )
        return


def setup_process(
    log_level: int,
    log_folder: str | None,
    log_file: str | None,
    db_folder: str | None,
) -> Callable[[], AppContext]:
    setup_logging(log_folder, log_file, do_rollover=False)
    set_log_level(log_level)
    set_db_location(db_folder)
    setup_db_adapters_and_converters()

    app = Flask(__name__)
    app.teardown_appcontext(close_db)
    return app.app_context


SERVER = Server()
