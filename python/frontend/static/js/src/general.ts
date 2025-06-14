/** @import { io } from 'socket.io-client'; */

import usingApiKey from './auth.js';

/* Types */
export interface Task {
    stop: boolean
    message: string
    action: string
    display_title: string
    category: string
    volume_id: number | null
    issue_id: number | null
}

export const url_base = (document.querySelector('#url_base') as HTMLButtonElement).dataset.value;
export const volume_id = parseInt(window.location.pathname.split('/').at(-1)!) || null;

//
// General functions
//
export function twoDigits(n: number) {
    return n.toLocaleString('en', { minimumFractionDigits: 2 });
};

export function setIcon(container: HTMLElement, icon: string, title = '') {
    container.title = title;
    container.innerHTML = icon;
};

export function setImage(container: HTMLElement, img: string, title = '') {
    container.title = title;
    container.querySelector('img')!.src = `${url_base}/static/img/${img}`;
};

export function hide(to_hide: HTMLElement[], to_show: HTMLElement[] | null = null) {
    to_hide.forEach((el) => {
        el.classList.add('hidden');
    });

    if (to_show !== null) {
        to_show.forEach((el) => {
            el.classList.remove('hidden');
        });
    }
};

export async function fetchAPI(endpoint: string, api_key: string, params = {}, json_return = true) {
    let formatted_params = '';

    if (Object.keys(params).length) {
        formatted_params = `&${Object.entries(params).map((p) => p.join('=')).join('&')}`;
    };

    return fetch(`${url_base}/api${endpoint}?api_key=${api_key}${formatted_params}`)
        .then((response) => {
            if (!response.ok) {
                return Promise.reject(response);
            }
            if (json_return) {
                return response.json();
            }
            else {
                return response;
            }
        })
        .catch((response) => {
            if (response.status === 401) {
                setLocalStorage({ api_key: null });
                window.location.href = `${url_base}/login?redirect=${window.location.pathname}`;
            }
            else {
                return Promise.reject(response);
            };
        });
};

export async function sendAPI(
    method: string, endpoint: string, api_key: string, params = {}, body = {},
) {
    let formatted_params = '';

    if (Object.keys(params).length) {
        formatted_params = `&${Object.entries(params).map((p) => p.join('=')).join('&')}`;
    };

    return fetch(`${url_base}/api${endpoint}?api_key=${api_key}${formatted_params}`, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    })
        .then((response) => {
            if (!response.ok) {
                return Promise.reject(response);
            }

            return response;
        })
        .catch((response) => {
            if (response.status === 401) {
                setLocalStorage({ api_key: null });
                window.location.href = `${url_base}/login?redirect=${window.location.pathname}`;
            }
            else {
                return Promise.reject(response);
            };
        });
};

//
// Icons
//
export const icons = {
    monitored: '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:svgjs="http://svgjs.com/svgjs" version="1.1" width="256" height="256" x="0" y="0" viewBox="0 0 24 24" style="enable-background:new 0 0 512 512" xml:space="preserve"><g><path d="M2.849,23.55a2.954,2.954,0,0,0,3.266-.644L12,17.053l5.885,5.853a2.956,2.956,0,0,0,2.1.881,3.05,3.05,0,0,0,1.17-.237A2.953,2.953,0,0,0,23,20.779V5a5.006,5.006,0,0,0-5-5H6A5.006,5.006,0,0,0,1,5V20.779A2.953,2.953,0,0,0,2.849,23.55Z"/></g></svg>',
    unmonitored: '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:svgjs="http://svgjs.com/svgjs" version="1.1" width="256" height="256" x="0" y="0" viewBox="0 0 24 24" style="enable-background:new 0 0 512 512" xml:space="preserve"><g><path d="M20.137,24a2.8,2.8,0,0,1-1.987-.835L12,17.051,5.85,23.169a2.8,2.8,0,0,1-3.095.609A2.8,2.8,0,0,1,1,21.154V5A5,5,0,0,1,6,0H18a5,5,0,0,1,5,5V21.154a2.8,2.8,0,0,1-1.751,2.624A2.867,2.867,0,0,1,20.137,24ZM6,2A3,3,0,0,0,3,5V21.154a.843.843,0,0,0,1.437.6h0L11.3,14.933a1,1,0,0,1,1.41,0l6.855,6.819a.843.843,0,0,0,1.437-.6V5a3,3,0,0,0-3-3Z"/></g></svg>',
};

export const images = {
    check: 'check.svg',
    cancel: 'cancel.svg',
};

//
// Tasks
//
export const task_to_button = {};

export function mapButtons(id: number | null) {
    if (window.location.pathname === '/' ||
      window.location.pathname === (`${url_base}/`)) {
        task_to_button['search_all'] = {
            button: document.querySelector('#searchall-button'),
            icon: `${url_base}/static/img/search.svg`,
            loading_icon: `${url_base}/static/img/loading.svg`,
        };
        task_to_button['update_all'] = {
            button: document.querySelector('#updateall-button'),
            icon: `${url_base}/static/img/refresh.svg`,
            loading_icon: `${url_base}/static/img/loading.svg`,
        };
    }
    else if (id !== null) {
        task_to_button[`refresh_and_scan#${id}`] = {
            button: document.querySelector('#refresh-button'),
            icon: `${url_base}/static/img/refresh.svg`,
            loading_icon: `${url_base}/static/img/loading.svg`,
        };
        task_to_button[`auto_search#${id}`] = {
            button: document.querySelector('#autosearch-button'),
            icon: `${url_base}/static/img/search.svg`,
            loading_icon: `${url_base}/static/img/loading.svg`,
        };
        task_to_button[`mass_rename#${id}`] = {
            button: document.querySelector('#rename-button'),
            icon: `${url_base}/static/img/rename.svg`,
            loading_icon: `${url_base}/static/img/loading.svg`,
        };
        task_to_button[`mass_convert#${id}`] = {
            button: document.querySelector('#convert-button'),
            icon: `${url_base}/static/img/convert.svg`,
            loading_icon: `${url_base}/static/img/loading.svg`,
        };

        (document.querySelectorAll('.issue-entry') as NodeListOf<HTMLButtonElement>).forEach((entry) => {
            task_to_button[`auto_search_issue#${id}#${entry.dataset.id}`] = {
                button: entry.querySelector('.action-column > button:first-child'),
                icon: `${url_base}/static/img/search.svg`,
                loading_icon: `${url_base}/static/img/loading.svg`,
            };
            task_to_button[`mass_convert_issue#${id}#${entry.dataset.id}`] = {
                button: entry.querySelector('.action-column > button:last-child'),
                icon: `${url_base}/static/img/convert.svg`,
                loading_icon: `${url_base}/static/img/loading.svg`,
            };
        });
    };
};

export function buildTaskString(task: Task) {
    let task_string = task.action;

    if (task.volume_id !== null) {
        task_string += `#${task.volume_id}`;
        if (task.issue_id !== null) {
            task_string += `#${task.issue_id}`;
        };
    };

    return task_string;
};

export function setTaskMessage(message: string) {
    const table = document.querySelector('#task-queue')!;

    table.innerHTML = '';
    if (message !== '') {
        const entry = document.createElement('p');

        entry.innerText = message;
        table.appendChild(entry);
    };
};

export function spinButton(task_string: string) {
    const button_info = task_to_button[task_string];
    const icon = button_info.button.querySelector('img');

    if (icon.src === button_info.loading_icon) {
        return;
    }

    icon.src = button_info.loading_icon;
    icon.classList.add('spinning');
};

export function unspinButton(task_string: string) {
    const button_info = task_to_button[task_string];
    const icon = button_info.button.querySelector('img');

    if (icon.src === button_info.icon) {
        return;
    }

    icon.src = button_info.icon;
    icon.classList.remove('spinning');
};

export function fillTaskQueue(api_key: string) {
    fetch(`${url_base}/api/system/tasks?api_key=${api_key}`, {
        priority: 'low',
    })
        .then((response) => {
            if (!response.ok) {
                return Promise.reject(response.status);
            }

            return response.json();
        })
        .then((json) => {
            setTaskMessage(json.result[0].message);
            (json.result as Task[]).forEach((task) => {
                const task_string = buildTaskString(task);

                if (task_string in task_to_button) {
                    spinButton(task_string);
                }
            });
        })
        .catch((e) => {
            if (e === 401) {
                setLocalStorage({ api_key: null });
                window.location.href = `${url_base}/login?redirect=${window.location.pathname}`;
            }
        });
};

export function handleTaskAdded(data: Task) {
    const task_string = buildTaskString(data);

    if (task_string in task_to_button) {
        spinButton(task_string);
    }
};

export function handleTaskRemoved(data: Task) {
    setTaskMessage('');

    const task_string = buildTaskString(data);

    if (task_string in task_to_button) {
        unspinButton(task_string);
    }
};

export function connectToWebSocket() {
    // @ts-expect-error remove this once we handle node_modules
    const socket = io({
        path: `${url_base}/api/socket.io`,
        transports: ['polling'],
        upgrade: false,
        autoConnect: false,
        closeOnBeforeunload: true,
    });

    socket.on('connect', () => console.log('Connected to WebSocket'));
    socket.on('disconnect', () => {
        console.log('Disconnected from WebSocket');
        setTimeout(() => window.location.reload(), 500);
    });

    socket.on('task_added', handleTaskAdded);
    socket.on('task_ended', handleTaskRemoved);
    socket.on('task_status', (data: Task) => setTaskMessage(data.message));
    socket.connect();

    return socket;
};

//
// Size conversion
//
export const sizes = {
    B: 1,
    KB: 1000,
    MB: 1000000,
    GB: 1000000000,
    TB: 1000000000000,
};

export function convertSize(size: number | null) {
    if (size === null || size <= 0) {
        return 'Unknown';
    }

    for (const [term, division_size] of Object.entries(sizes)) {
        const resulting_size = size / division_size;

        if (0 <= resulting_size && resulting_size <= 1000) {
            return `${twoDigits(Math.round((size / division_size * 100)) / 100)} ${term}`;
        };
    };

    return `${(Math.round((size / sizes.TB * 100)) / 100).toString()} TB`;
};

//
// LocalStorage
//
export const default_values = {
    lib_sorting: 'title',
    lib_view: 'posters',
    lib_filter: '',
    theme: 'light',
    translated_filter: 'all',
    api_key: null,
    last_login: 0,
    monitor_new_volume: true,
    monitor_new_issues: true,
    monitoring_scheme: 'all',
};

export function setupLocalStorage() {
    if (!localStorage.getItem('kapowarr')) {
        localStorage.setItem('kapowarr', JSON.stringify(default_values));
    }

    const missing_keys = [
        ...Object.keys(default_values),
    ].filter((e) =>
        ![...Object.keys(JSON.parse(localStorage.getItem('kapowarr') ?? ''))].includes(e));

    if (missing_keys.length) {
        const storage = JSON.parse(localStorage.getItem('kapowarr') ?? '');

        missing_keys.forEach((missing_key) => {
            storage[missing_key] = default_values[missing_key];
        });

        localStorage.setItem('kapowarr', JSON.stringify(storage));
    };
};

export function getLocalStorage(...keys: string[]) {
    const storage = JSON.parse(localStorage.getItem('kapowarr') ?? '');
    const result = {} as Record<string, string>;

    for (const key of keys) {
        result[key] = storage[key];
    }

    return result;
};

export function setLocalStorage(keys_values: Record<string, string | boolean | null>) {
    const storage = JSON.parse(localStorage.getItem('kapowarr') ?? '');

    for (const [key, value] of Object.entries(keys_values)) {
        storage[key] = value;
    }

    localStorage.setItem('kapowarr', JSON.stringify(storage));
};

// code run on load

mapButtons(volume_id);

usingApiKey()
    .then((api_key) => {
        setTimeout(() => fillTaskQueue(api_key), 200);
    });

setupLocalStorage();
if (getLocalStorage('theme')['theme'] === 'dark') {
    document.querySelector(':root')?.classList.add('dark-mode');
}

export const socket = connectToWebSocket();

(document.querySelector('#toggle-nav') as HTMLButtonElement).onclick = () =>
    document.querySelector('#nav-bar')?.classList.toggle('show-nav');
