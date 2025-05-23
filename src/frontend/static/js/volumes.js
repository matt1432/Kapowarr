const library_els = {
    pages: {
        loading: document.querySelector('#loading-library'),
        empty: document.querySelector('#empty-library'),
        view: document.querySelector('#library-container'),
    },
    views: {
        list: document.querySelector('#list-library'),
        table: document.querySelector('#table-library'),
    },
    view_options: {
        sort: document.querySelector('#sort-button'),
        view: document.querySelector('#view-button'),
        filter: document.querySelector('#filter-button'),
    },
    task_buttons: {
        update_all: document.querySelector('#updateall-button'),
        search_all: document.querySelector('#searchall-button'),
    },
    search: {
        clear: document.querySelector('#clear-search'),
        container: document.querySelector('#search-container'),
        input: document.querySelector('#search-input'),
    },
    stats: {
        volume_count: document.querySelector('#volume-count'),
        volume_monitored_count: document.querySelector('#volume-monitored-count'),
        volume_unmonitored_count: document.querySelector('#volume-unmonitored-count'),
        issue_count: document.querySelector('#issue-count'),
        issue_download_count: document.querySelector('#issue-download-count'),
        file_count: document.querySelector('#file-count'),
        total_file_size: document.querySelector('#total-file-size'),
    },
    mass_edit: {
        bar: document.querySelector('.action-bar'),
        button: document.querySelector('#massedit-button'),
        toggle: document.querySelector('#massedit-toggle'),
        select_all: document.querySelector('#selectall-input'),
        cancel: document.querySelector('#cancel-massedit'),
    },
};

const pre_build_els = {
    list_entry: document.querySelector('.pre-build-els .list-entry'),
    table_entry: document.querySelector('.pre-build-els .table-entry'),
};

function showLibraryPage(el) {
    hide(Object.values(library_els.pages), [el]);
};

class LibraryEntry {
    constructor(id, api_key) {
        this.id = id;
        this.api_key = api_key;
        this.list_entry = library_els.views.list.querySelector(`.vol-${id}`);
        this.table_entry = library_els.views.table.querySelector(`.vol-${id}`);
    };

    setMonitored(monitored) {
        sendAPI('PUT', `/volumes/${this.id}`, this.api_key, {}, {
            monitored,
        })
            .then(() => {
                const monitored_button = this.table_entry.querySelector('.table-monitored');

                monitored_button.onclick = () => new LibraryEntry(this.id, this.api_key)
                    .setMonitored(!monitored);

                if (monitored) {
                    this.list_entry.setAttribute('monitored', '');
                    setIcon(monitored_button, icons.monitored, 'Monitored');
                }
                else {
                    this.list_entry.removeAttribute('monitored');
                    setIcon(monitored_button, icons.unmonitored, 'Unmonitored');
                };
            });
    };
};

function populateLibrary(volumes, api_key) {
    library_els.views.list.querySelectorAll('.list-entry').forEach(
        (e) => {
            e.remove();
        },
    );
    library_els.views.table.innerHTML = '';
    const space_taker = document.querySelector('.space-taker');

    volumes.forEach((volume) => {
        const list_entry = pre_build_els.list_entry.cloneNode(true);
        const table_entry = pre_build_els.table_entry.cloneNode(true);

        // Label
        const label = `View the volume ${volume.title} (${volume.year}) Volume ${volume.volume_number}`;

        list_entry.ariaLabel = label;
        table_entry.ariaLabel = label;

        // ID
        list_entry.classList.add(`vol-${volume.id}`);
        table_entry.classList.add(`vol-${volume.id}`);
        table_entry.dataset.id = volume.id;

        // Link
        const link = `${url_base}/volumes/${volume.id}`;

        list_entry.href = link;
        table_entry.querySelector('.table-link').href = link;

        // Cover
        list_entry.querySelector('.list-img').src =
            `${url_base}/api/volumes/${volume.id}/cover?api_key=${api_key}`;

        // Title
        const list_title = list_entry.querySelector('.list-title');
        const list_title_label = `${volume.title} (${volume.year})`;

        list_title.innerText = list_title_label;
        list_title.title = list_title_label;

        table_entry.querySelector('.table-link').innerText = volume.title;

        // Year
        table_entry.querySelector('.table-year').innerText = volume.year;

        // Volume Number
        const volume_num = `Volume ${volume.volume_number}`;

        list_entry.querySelector('.list-volume').innerText = volume_num;
        table_entry.querySelector('.table-volume').innerText = volume_num;

        // Progress Bar
        const progress = (volume.issues_downloaded_monitored / volume.issue_count_monitored * 100);
        const list_bar = list_entry.querySelector('.list-prog-bar');
        const table_bar = table_entry.querySelector('.table-prog-bar');

        const progress_text = `${volume.issues_downloaded_monitored}/${volume.issue_count_monitored}`;

        list_entry.querySelector('.list-prog-num').innerText = progress_text;
        table_entry.querySelector('.table-prog-num').innerText = progress_text;

        list_bar.style.width = `${progress}%`;
        table_bar.style.width = `${progress}%`;


        if (progress === 100) {
            list_bar.style.backgroundColor = 'var(--success-color)';
            table_bar.style.backgroundColor = 'var(--success-color)';
        }

        else if (volume.monitored === true) {
            list_bar.style.backgroundColor = 'var(--accent-color)';
            table_bar.style.backgroundColor = 'var(--accent-color)';
        }

        else {
            list_bar.style.backgroundColor = 'var(--error-color)';
            table_bar.style.backgroundColor = 'var(--error-color)';
        }

        // Monitored
        const monitored_button = table_entry.querySelector('.table-monitored');

        monitored_button.onclick = () => new LibraryEntry(volume.id, api_key)
            .setMonitored(!volume.monitored);

        if (volume.monitored) {
            list_entry.setAttribute('monitored', '');
            setIcon(monitored_button, icons.monitored, 'Monitored');
        }
        else {
            setIcon(monitored_button, icons.unmonitored, 'Unmonitored');
        }

        // Add to view
        library_els.views.list.insertBefore(list_entry, space_taker);
        library_els.views.table.appendChild(table_entry);
    });
};

function fetchLibrary(api_key) {
    showLibraryPage(library_els.pages.loading);

    const params = {
        sort: library_els.view_options.sort.value,
        filter: library_els.view_options.filter.value,
    };
    const query = library_els.search.input.value;

    if (query !== '') {
        params.query = query;
    }

    fetchAPI('/volumes', api_key, params).then((json) => {
        if (json.result.length === 0) {
            showLibraryPage(library_els.pages.empty);
        }
        else {
            populateLibrary(json.result, api_key);
            showLibraryPage(library_els.pages.view);
        };
    });
};

// eslint-disable-next-line
function searchLibrary() {
    usingApiKey().then((api_key) => fetchLibrary(api_key));
};

function clearSearch(api_key) {
    library_els.search.input.value = '';
    fetchLibrary(api_key);
};

function fetchStats(api_key) {
    fetchAPI('/volumes/stats', api_key)
        .then((json) => {
            library_els.stats.volume_count.innerText = json.result.volumes;
            library_els.stats.volume_monitored_count.innerText = json.result.monitored;
            library_els.stats.volume_unmonitored_count.innerText = json.result.unmonitored;
            library_els.stats.issue_count.innerText = json.result.issues;
            library_els.stats.issue_download_count.innerText = json.result.downloaded_issues;
            library_els.stats.file_count.innerText = json.result.files;
            library_els.stats.total_file_size.innerText = json.result.total_file_size > 0 ?
                convertSize(json.result.total_file_size) :
                '0 MB';
        });
};

//
// Mass Edit
//
function runAction(api_key, action, args = {}) {
    showLibraryPage(library_els.pages.loading);

    const volume_ids = [...library_els.views.table.querySelectorAll(
        'input[type="checkbox"]:checked',
    )].map((v) => parseInt(v.parentNode.parentNode.dataset.id));

    sendAPI('POST', '/masseditor', api_key, {}, {
        volume_ids,
        action,
        args,
    })
        .then(() => {
            library_els.mass_edit.select_all.checked = false;
            fetchLibrary(api_key);
        });
};

// code run on load

const lib_options = getLocalStorage('lib_sorting', 'lib_view', 'lib_filter');

library_els.view_options.sort.value = lib_options.lib_sorting;
library_els.view_options.view.value = lib_options.lib_view;
library_els.view_options.filter.value = lib_options.lib_filter;

usingApiKey().then((api_key) => {
    fetchLibrary(api_key);
    fetchStats(api_key);

    library_els.search.clear.onclick = () => clearSearch(api_key);

    library_els.task_buttons.update_all.onclick = () => sendAPI(
        'POST', '/system/tasks', api_key, {}, { cmd: 'update_all' },
    );
    library_els.task_buttons.search_all.onclick = () => sendAPI(
        'POST', '/system/tasks', api_key, {}, { cmd: 'search_all' },
    );

    library_els.view_options.sort.onchange = () => {
        setLocalStorage({ lib_sorting: library_els.view_options.sort.value });
        fetchLibrary(api_key);
    };
    library_els.view_options.view.onchange = () => setLocalStorage({
        lib_view: library_els.view_options.view.value,
    });
    library_els.view_options.filter.onchange = () => {
        setLocalStorage({ lib_filter: library_els.view_options.filter.value });
        fetchLibrary(api_key);
    };

    const edit_action = () => {
        const toggle = library_els.mass_edit.toggle;

        if (toggle.hasAttribute('checked')) {
            toggle.removeAttribute('checked');
        }
        else {
            const select = document.querySelector('select[name="root_folder_id"]');

            if (select.querySelector('option') === null) {
                fetchAPI('/rootfolder', api_key)
                    .then((json) => {
                        json.result.forEach((rf) => {
                            const entry = document.createElement('option');

                            entry.value = rf.id;
                            entry.innerText = rf.folder;
                            select.appendChild(entry);
                        });
                        toggle.setAttribute('checked', '');
                    });
            }
            else {
                toggle.setAttribute('checked', '');
            }
        }
    };

    library_els.mass_edit.button.onclick = edit_action;
    library_els.mass_edit.cancel.onclick = edit_action;

    library_els.mass_edit.bar.querySelectorAll('.action-divider > button[data-action]').forEach(
        (b) => {
            b.onclick = (e) => runAction(api_key, e.target.dataset.action);
        },
    );
    library_els.mass_edit.bar
        .querySelector('button[data-action="delete"]')
        .onclick = (e) => runAction(
            api_key,
            e.target.dataset.action,
            {
                delete_folder: document.querySelector(
                    'select[name="delete_folder"]',
                ).value === 'true',
            },
        );
    library_els.mass_edit.bar
        .querySelector('button[data-action="root_folder"]')
        .onclick = (e) => runAction(
            api_key,
            e.target.dataset.action,
            {
                root_folder_id: parseInt(document.querySelector(
                    'select[name="root_folder_id"]',
                ).value),
            },
        );
    library_els.mass_edit.bar
        .querySelector('button[data-action="monitoring_scheme"]')
        .onclick = (e) => runAction(
            api_key,
            e.target.dataset.action,
            {
                monitoring_scheme: document.querySelector(
                    'select[name="monitoring_scheme"]',
                ).value,
            },
        );
});

library_els.search.container.action = 'javascript:searchLibrary();';
library_els.mass_edit.select_all.onchange = () => library_els.views.table
    .querySelectorAll('input[type="checkbox"]')
    .forEach((c) => {
        c.checked = library_els.mass_edit.select_all.checked;
    });
