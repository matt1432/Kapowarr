const SearchEls = {
    pre_build: {
        search_entry: document.querySelector('.pre-build-els .search-entry'),
    },
    search_bar: {
        bar: document.querySelector('.search-bar'),
        cancel: document.querySelector('#search-cancel-button'),
        input: document.querySelector('#search-input'),
    },
    search_results: document.querySelector('#search-results'),
    msgs: {
        blocked: document.querySelector('#search-blocked'),
        failed: document.querySelector('#search-failed'),
        empty: document.querySelector('#search-empty'),
        explain: document.querySelector('#search-explain'),
        loading: document.querySelector('#search-loading'),
    },
    filters: {
        translations: document.querySelector('#filter-translations'),
        publisher: document.querySelector('#filter-publisher'),
        volume_number: document.querySelector('#filter-volume-number'),
        year: document.querySelector('#filter-year'),
        issue_count: document.querySelector('#filter-issue-count'),
    },
    window: {
        form: document.querySelector('#add-form'),
        title: document.querySelector('#add-window h2'),
        cover: document.querySelector('#add-cover'),
        cv_input: document.querySelector('#comicvine-input'),
        monitor_volume_input: document.querySelector('#monitor-volume-input'),
        monitor_issues_input: document.querySelector('#monitor-issues-input'),
        monitoring_scheme: document.querySelector('#monitoring-scheme-input'),
        root_folder_input: document.querySelector('#rootfolder-input'),
        volume_folder_input: document.querySelector('#volumefolder-input'),
        special_state_input: document.querySelector('#specialoverride-input'),
        auto_search_input: document.querySelector('#auto-search-input'),
        submit: document.querySelector('#add-volume'),
    },
};

//
// Searching
//
function addAlreadyAdded(entry, id) {
    entry.onclick = () => {
        window.location.href = `${url_base}/volumes/${id}`;
    };

    const title = entry.querySelector('h2');
    const aa_icon = document.createElement('img');

    aa_icon.src = `${url_base}/static/img/check_circle.svg`;
    aa_icon.alt = 'Volume is already added';
    title.appendChild(aa_icon);
};

function buildResults(results, api_key) {
    SearchEls.search_results
        .querySelectorAll('button:not(.filter-bar)')
        .forEach((e) => {
            e.remove();
        });
    results.forEach((result) => {
        const entry = SearchEls.pre_build.search_entry.cloneNode(true);

        const _title =
            result.year !== null ?
            `${result.title} (${result.year})` :
                result.title;

        entry.dataset.title = _title;
        entry.ariaLabel = _title;

        entry.dataset.cover = result.cover_link;
        entry.dataset.comicvine_id = result.comicvine_id;
        entry.dataset._translated = result.translated;
        entry.dataset._title = result.title;
        entry.dataset._year = result.year || '';
        entry.dataset._volume_number = result.volume_number;
        entry.dataset._publisher = result.publisher || '';
        entry.dataset._issue_count = result.issue_count;

        // Only allow adding volume if it isn't already added
        if (result.already_added === null) {
            entry.onclick = () => showAddWindow(result.comicvine_id, api_key);
        }

        entry.querySelector('img').src = result.cover_link;

        const title = entry.querySelector('h2');

        title.innerText = result.title;

        if (result.year !== null) {
            const year = document.createElement('span');

            year.innerText = ` (${result.year})`;
            title.appendChild(year);
        };

        if (result.already_added !== null) {
            addAlreadyAdded(entry, result.already_added);
        }

        const tags = entry.querySelector('.entry-tags');

        if (result.volume_number !== null) {
            const volume_number = document.createElement('p');

            volume_number.innerText = `Volume ${result.volume_number}`;
            tags.appendChild(volume_number);
        };

        const publisher = document.createElement('p');

        publisher.innerText = result.publisher || 'Publisher Unknown';
        tags.appendChild(publisher);

        const issue_count = document.createElement('p');

        issue_count.innerText = `${result.issue_count} issues`;
        tags.appendChild(issue_count);

        const info_link = document.createElement('a');

        info_link.href = result.site_url;
        info_link.innerText = 'Link';
        info_link.onclick = (e) => e.stopImmediatePropagation();
        tags.appendChild(info_link);

        if (result.aliases.length) {
            const aliases = entry.querySelector('.entry-aliases');

            result.aliases.forEach((alias_text) => {
                const alias = document.createElement('p');

                alias.innerText = alias_text;
                aliases.appendChild(alias);
            });
        };

        entry.querySelectorAll('.entry-description, .entry-spare-description')
            .forEach(
                (d) => {
                    d.innerHTML = result.description;
                },
            );

        SearchEls.search_results.appendChild(entry);
    });

    // Fill filters
    const years = new Set(results.map((r) => r.year).sort());

    SearchEls.filters.year.innerHTML = '';
    const all_years_option = document.createElement('option');

    all_years_option.value = '';
    all_years_option.innerText = 'All Years';
    all_years_option.selected = true;
    SearchEls.filters.year.appendChild(all_years_option);

    years.forEach((y) => {
        const entry = document.createElement('option');

        if (y === null) {
            entry.value = y;
            entry.innerText = '(No Year)';
        }
        else {
            entry.value = y;
            entry.innerText = y;
        };
        SearchEls.filters.year.appendChild(entry);
    });

    const issue_counts = new Set(results
        .map((r) => r.issue_count)
        .sort((a, b) => a - b));

    SearchEls.filters.issue_count.innerHTML = '';
    const all_issue_counts_option = document.createElement('option');

    all_issue_counts_option.value = '';
    all_issue_counts_option.innerText = 'All Issue Counts';
    all_issue_counts_option.selected = true;
    SearchEls.filters.issue_count.appendChild(all_issue_counts_option);
    const one_higher_issue_counts_option = document.createElement('option');

    one_higher_issue_counts_option.value = '>1 issues';
    one_higher_issue_counts_option.innerText = '>1 issues';
    SearchEls.filters.issue_count.appendChild(one_higher_issue_counts_option);

    issue_counts.forEach((ic) => {
        const entry = document.createElement('option');

        entry.innerText = `${ic} issues`;
        entry.value = `${ic} issues`;
        SearchEls.filters.issue_count.appendChild(entry);
    });

    const volume_numbers = new Set(results
        .map((r) => r.volume_number)
        .sort((a, b) => a - b));

    SearchEls.filters.volume_number.innerHTML = '';
    const all_volume_numbers_option = document.createElement('option');

    all_volume_numbers_option.value = '';
    all_volume_numbers_option.innerText = 'All Volume Numbers';
    all_volume_numbers_option.selected = true;
    SearchEls.filters.volume_number.appendChild(all_volume_numbers_option);

    volume_numbers.forEach((vn) => {
        const entry = document.createElement('option');

        entry.value = `Volume ${vn}`;
        entry.innerText = `Volume ${vn}`;
        SearchEls.filters.volume_number.appendChild(entry);
    });

    const publishers = new Set(results.map((r) => r.publisher).sort());

    SearchEls.filters.publisher.innerHTML = '';
    const all_publishers_option = document.createElement('option');

    all_publishers_option.value = '';
    all_publishers_option.innerText = 'All Publishers';
    all_publishers_option.selected = true;
    SearchEls.filters.publisher.appendChild(all_publishers_option);

    publishers.forEach((pub) => {
        const entry = document.createElement('option');

        entry.value = pub;
        entry.innerText = pub;
        SearchEls.filters.publisher.appendChild(entry);
    });

    processURLFilters();
    applyFilters();
};

function search(reset_url_params = true) {
    if (!SearchEls.msgs.blocked.classList.contains('hidden')) {
        return;
    }

    SearchEls.search_bar.input.blur();

    hide([
        SearchEls.msgs.empty,
        SearchEls.msgs.explain,
        SearchEls.msgs.failed,
        SearchEls.search_results,
    ], [
        SearchEls.msgs.loading,
    ]);

    if (reset_url_params) {
        emptyParams();
    }

    usingApiKey().then((api_key) => {
        const query = SearchEls.search_bar.input.value;

        fetchAPI('/volumes/search', api_key, { query })
            .then((json) => {
                buildResults(json.result, api_key);

                if (!SearchEls.search_results.querySelector('button:not(.filter-bar)')) {
                    hide([SearchEls.msgs.loading], [SearchEls.msgs.empty]);
                }
                else {
                    hide([SearchEls.msgs.loading], [SearchEls.search_results]);
                }
            })
            .catch((e) => {
                if (e.status === 400) {
                    hide([SearchEls.msgs.loading], [SearchEls.msgs.failed]);
                }
                else {
                    console.log(e);
                }
            });
    });
};

function clearSearch() {
    hide([
        SearchEls.search_results,
        SearchEls.msgs.empty,
        SearchEls.msgs.failed,
    ], [
        SearchEls.msgs.explain,
    ]);
    SearchEls.search_results
        .querySelectorAll('button:not(.filter-bar)')
        .forEach((e) => {
            e.remove();
        });
    SearchEls.search_bar.input.value = '';
    setURLParams();
};

function applyFilters() {
    const translation = SearchEls.filters.translations.value;
    const year = SearchEls.filters.year.value;
    const issue_count = (
        SearchEls.filters.issue_count.value || ' issues'
    ).split(' issues')[0];
    const volume_number = (
        SearchEls.filters.volume_number.value || 'Volume '
    ).split('Volume ')[1];
    const publisher = SearchEls.filters.publisher.value;

    setLocalStorage({ translated_filter: translation });

    let filter = '';

    if (translation === 'only-english') {
        filter += '[data-_translated="false"]';
    }
    if (year !== '') {
        filter += `[data-_year="${year}"]`;
    }
    if (issue_count === '>1') {
        filter += ':not([data-_issue_count="0"]):not([data-_issue_count="1"])';
    }
    else if (issue_count !== '') {
        filter += `[data-_issue_count="${issue_count}"]`;
    }
    if (volume_number !== '') {
        filter += `[data-_volume_number="${volume_number}"]`;
    }
    if (publisher !== '') {
        filter += `[data-_publisher="${publisher}"]`;
    }

    if (filter === '') {
        hide([], SearchEls.search_results.querySelectorAll('button'));
    }
    else {
        hide(
            SearchEls.search_results.querySelectorAll('button'),
            SearchEls.search_results.querySelectorAll(`button${filter}`),
        );
    }

    setURLParams();
};

//
// URL params
//
function emptyParams() {
    history.pushState(
        {}, '', window.location.origin + window.location.pathname,
    );
};

function setURLParams() {
    const params = new URLSearchParams();

    if (SearchEls.search_bar.input.value === '') {
        emptyParams();

        return;
    };

    if (SearchEls.search_bar.input.value) {
        params.set('q', SearchEls.search_bar.input.value);
    }
    if (SearchEls.filters.translations.value) {
        params.set('t', SearchEls.filters.translations.value);
    }
    if (SearchEls.filters.year.value) {
        params.set('y', SearchEls.filters.year.value);
    }
    if (SearchEls.filters.issue_count.value) {
        params.set('i', SearchEls.filters.issue_count.value);
    }
    if (SearchEls.filters.volume_number.value) {
        params.set('v', SearchEls.filters.volume_number.value);
    }
    if (SearchEls.filters.publisher.value) {
        params.set('p', SearchEls.filters.publisher.value);
    }

    history.pushState({}, '', `?${params.toString()}`);
};

function processURLParams() {
    const params = new URLSearchParams(window.location.search);

    const query = params.get('q');

    if ((query || null) === null) {
        return;
    }
    SearchEls.search_bar.input.value = query;

    search(false);
};

function processURLFilters() {
    const params = new URLSearchParams(window.location.search);

    if (params.get('t')) {
        SearchEls.filters.translations.value = params.get('t');
    }
    if (params.get('y')) {
        SearchEls.filters.year.value = params.get('y');
    }
    if (params.get('i')) {
        SearchEls.filters.issue_count.value = params.get('i');
    }
    if (params.get('v')) {
        SearchEls.filters.volume_number.value = params.get('v');
    }
    if (params.get('p')) {
        SearchEls.filters.publisher.value = params.get('p');
    }
};

//
// Adding
//
function fillRootFolderInput(api_key) {
    fetchAPI('/rootfolder', api_key).then((json) => {
        if (json.result.length) {
            json.result.forEach((folder) => {
                const option = document.createElement('option');

                option.value = folder.id;
                option.innerText = folder.folder;
                SearchEls.window.root_folder_input.appendChild(option);
            });
        }
        else {
            hide([], [SearchEls.msgs.blocked]);
        }
    });
};

function showAddWindow(comicvine_id, api_key) {
    const volume_data = document.querySelector(
        `button[data-comicvine_id="${comicvine_id}"]`,
    ).dataset;
    const body = {
        comicvine_id: volume_data.comicvine_id,
        title: volume_data._title,
        year: volume_data._year || null,
        volume_number: volume_data._volume_number,
        publisher: volume_data._publisher || null,
    };

    sendAPI('POST', '/volumes/search', api_key, {}, body)
        .then((response) => response.json())
        .then((json) => {
            volume_data._volume_folder = json.result.folder;
            SearchEls.window.volume_folder_input.value = json.result.folder;
            showWindow('add-window');
        });

    SearchEls.window.title.innerText = volume_data.title;
    SearchEls.window.cover.src = volume_data.cover;
    SearchEls.window.cv_input.value = comicvine_id;
    SearchEls.window.special_state_input.value = 'auto';

    const monitoring_pref = getLocalStorage(
        'monitor_new_volume', 'monitor_new_issues', 'monitoring_scheme',
    );

    SearchEls.window.monitor_volume_input.value = monitoring_pref.monitor_new_volume;
    SearchEls.window.monitor_issues_input.value = monitoring_pref.monitor_new_issues;
    SearchEls.window.monitoring_scheme.value = monitoring_pref.monitoring_scheme;
};

// eslint-disable-next-line
function addVolume() {
    showLoadWindow('add-window');
    const volume_folder = SearchEls.window.volume_folder_input.value;

    const data = {
        comicvine_id: parseInt(SearchEls.window.cv_input.value),
        root_folder_id: parseInt(SearchEls.window.root_folder_input.value),
        monitor: SearchEls.window.monitor_volume_input.value === 'true',
        monitoring_scheme: SearchEls.window.monitoring_scheme.value,
        monitor_new_issues: SearchEls.window.monitor_issues_input.value === 'true',
        volume_folder: '',
        special_version: SearchEls.window.special_state_input.value || null,
        auto_search: SearchEls.window.auto_search_input.checked,
    };

    if (
        volume_folder !== '' &&
        volume_folder !== document.querySelector(
            `button[data-comicvine_id="${data.comicvine_id}"]`,
        ).dataset._volume_folder
    ) {
        // Custom volume folder
        data.volume_folder = volume_folder;
    };

    setLocalStorage({
        monitor_new_volume: data.monitor,
        monitor_new_issues: data.monitor_new_issues,
        monitoring_scheme: data.monitoring_scheme,
    });

    usingApiKey()
        .then((api_key) => {
            sendAPI('POST', '/volumes', api_key, {}, data)
                .then((response) => response.json())
                .then((json) => {
                    const entry = document.querySelector(
                `button[data-comicvine_id="${data.comicvine_id}"]`,
                    );

                    addAlreadyAdded(entry, json.result.id);
                    closeWindow();
                })
                .catch((e) => {
                    if (e.status === 509) {
                        SearchEls.window.submit.innerText = 'ComicVine API rate limit reached';
                        showWindow('add-window');
                    }
                    else {
                        console.log(e);
                    }
                });
        });
};

// code run on load
usingApiKey()
    .then((api_key) => fillRootFolderInput(api_key));

SearchEls.search_bar.cancel.onclick = () => clearSearch();
SearchEls.window.form.action = 'javascript:addVolume();';
SearchEls.search_bar.bar.action = 'javascript:search();';

SearchEls.filters.translations.onchange = () => applyFilters();
SearchEls.filters.publisher.onchange = () => applyFilters();
SearchEls.filters.volume_number.onchange = () => applyFilters();
SearchEls.filters.year.onchange = () => applyFilters();
SearchEls.filters.issue_count.onchange = () => applyFilters();

const translated_filter = getLocalStorage('translated_filter')['translated_filter'];

SearchEls.filters.translations
    .querySelector(`option[value="${translated_filter}"]`)
    .setAttribute('selected', '');

processURLParams();
