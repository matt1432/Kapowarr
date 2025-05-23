function fillSettings(api_key) {
    fetchAPI('/settings', api_key)
        .then((json) => {
            document.querySelector('#download-folder-input').value = json.result.download_folder;
            document.querySelector('#concurrent-direct-downloads-input').value = json.result
                .concurrent_direct_downloads;
            document.querySelector('#torrent-timeout-input').value = (
                (json.result.failing_torrent_timeout || 0) / 60
            ) || '';
            document.querySelector('#seeding-handling-input').value = json.result.seeding_handling;
            document.querySelector('#delete-torrents-input').checked = json.result
                .delete_completed_torrents;
            fillPref(json.result.service_preference);
        });
};

function saveSettings(api_key) {
    document.querySelector('#save-button p').innerText = 'Saving';
    document.querySelector('#download-folder-input').classList.remove('error-input');
    const data = {
        download_folder: document.querySelector('#download-folder-input').value,
        concurrent_direct_downloads: parseInt(
            document.querySelector('#concurrent-direct-downloads-input').value,
        ),
        failing_torrent_timeout: parseInt(
            document.querySelector('#torrent-timeout-input').value || 0,
        ) * 60,
        seeding_handling: document.querySelector('#seeding-handling-input').value,
        delete_completed_torrents: document.querySelector('#delete-torrents-input').checked,
        service_preference: [...document.querySelectorAll('#pref-table select')].map((e) => e.value),
    };

    sendAPI('PUT', '/settings', api_key, {}, data)
        .then(() => {
            document.querySelector('#save-button p').innerText = 'Saved';
        })
        .catch(() => {
            document.querySelector('#save-button p').innerText = 'Failed';
            e.json().then((e) => {
                if (
                    (e.error === 'InvalidSettingValue' && e.result.key === 'download_folder') ||
                    e.error === 'FolderNotFound'
                ) {
                    document.querySelector('#download-folder-input').classList.add('error-input');
                }

                else {
                    console.log(e);
                }
            });
        });
};

//
// Empty download folder
//
function emptyFolder(api_key) {
    sendAPI('DELETE', '/activity/folder', api_key).then(() => {
        document.querySelector('#empty-download-folder').innerText = 'Done';
    });
};

//
// Service preference
//
function fillPref(pref) {
    const selects = document.querySelectorAll('#pref-table select');

    for (let i = 0; i < pref.length; i++) {
        const service = pref[i];
        const select = selects[i];

        select.onchange = updatePrefOrder;
        pref.forEach((option) => {
            const entry = document.createElement('option');

            entry.value = option;
            entry.innerText = option.charAt(0).toUpperCase() + option.slice(1);
            if (option === service) {
                entry.selected = true;
            }
            select.appendChild(entry);
        });
    };
};

function updatePrefOrder(e) {
    const other_selects = document.querySelectorAll(
        `#pref-table select:not([data-place="${e.target.dataset.place}"])`,
    );

    // Find select that has the value of the target select
    for (const select of other_selects) {
        if (select.value === e.target.value) {
            // Set it to old value of target select
            all_values = [...document.querySelector('#pref-table select').options].map((s) => s.value);
            used_values = new Set([
                ...document.querySelectorAll('#pref-table select'),
            ].map((s) => s.value));

            open_value = all_values.filter((v) => !used_values.has(v))[0];
            select.value = open_value;
            break;
        };
    };
};

// code run on load
usingApiKey()
    .then((api_key) => {
        fillSettings(api_key);

        document.querySelector('#save-button').onclick = () => saveSettings(api_key);
        document.querySelector('#empty-download-folder').onclick = () => emptyFolder(api_key);
    });
