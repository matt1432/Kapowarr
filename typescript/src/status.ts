import usingApiKey from './auth.js';
import { fetchAPI, sendAPI } from './general.js';

const StatEls = {
    version: document.querySelector('#version') as HTMLTableCellElement,
    python_version: document.querySelector('#python-version') as HTMLTableCellElement,
    database_version: document.querySelector('#database-version') as HTMLTableCellElement,
    database_location: document.querySelector('#database-location') as HTMLTableCellElement,
    data_folder: document.querySelector('#data-folder') as HTMLTableCellElement,
    buttons: {
        copy: document.querySelector('#copy-about') as HTMLButtonElement,
        restart: document.querySelector('#restart-button') as HTMLButtonElement,
        shutdown: document.querySelector('#shutdown-button') as HTMLButtonElement,
    },
};

const about_table = `
| Key| Value |
|--------|--------|
| Kapowarr version | {k_version} |
| Python version | {p_version} |
| Database version | {d_version} |
| Database location | {d_loc} |
| Data folder | {folder} |

`;

// code run on load

usingApiKey().then((api_key) => {
    fetchAPI('/system/about', api_key).then((json) => {
        StatEls.version.innerText = json.result.version;
        StatEls.python_version.innerText = json.result.python_version;
        StatEls.database_version.innerText = json.result.database_version;
        StatEls.database_location.innerText = json.result.database_location;
        StatEls.data_folder.innerText = json.result.data_folder;

        StatEls.buttons.copy.onclick = () => {
            copy(about_table
                .replace('{k_version}', json.result.version)
                .replace('{p_version}', json.result.python_version)
                .replace('{d_version}', json.result.database_version)
                .replace('{d_loc}', json.result.database_location)
                .replace('{folder}', json.result.data_folder));
        };
    });

    StatEls.buttons.restart.onclick = () => {
        StatEls.buttons.restart.innerText = 'Restarting';
        sendAPI('POST', '/system/power/restart', api_key);
    };

    StatEls.buttons.shutdown.onclick = () => {
        StatEls.buttons.shutdown.innerText = 'Shutting down';
        sendAPI('POST', '/system/power/shutdown', api_key);
    };
});


function copy(text: string) {
    const range = document.createRange();
    const selection = document.getSelection();

    const container = document.createElement('span');

    container.textContent = text;
    container.ariaHidden = 'true';
    container.style.all = 'unset';
    container.style.position = 'fixed';
    container.style.top = '0';
    container.style.clip = 'rect(0, 0, 0, 0)';
    container.style.whiteSpace = 'pre';
    container.style.userSelect = 'text';

    document.body.appendChild(container);

    try {
        range.selectNodeContents(container);
        selection?.addRange(range);
        document.execCommand('copy');
        StatEls.buttons.copy.innerText = 'Copied';
    }
    catch (_e) {
        // Failed
        StatEls.buttons.copy.innerText = 'Failed';
    }
    finally {
        selection?.removeAllRanges();
        document.body.removeChild(container);
    }
}
