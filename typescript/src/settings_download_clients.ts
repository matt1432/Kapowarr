import usingApiKey from './auth.js';

import WindowFuncs from './window.js';
import { hide, fetchAPI, sendAPI } from './general.js';

/* Types */
export interface ExternalClient {
    id: number
    download_type: string
    client_type: string
    title: string
    base_url: string
    username: string | null
    password: string | null
    api_token: string
}

export interface CredentialData {
    id: number
    source: string
    username: string | null
    email: string | null
    password: string | null
    api_key: string | null
}

function createUsernameInput(id: string) {
    const username_row = document.createElement('tr');
    const username_header = document.createElement('th');
    const username_label = document.createElement('label');

    username_label.innerText = 'Username';
    username_label.setAttribute('for', id);
    username_header.appendChild(username_label);
    username_row.appendChild(username_header);
    const username_container = document.createElement('td');
    const username_input = document.createElement('input');

    username_input.type = 'text';
    username_input.id = id;
    username_container.appendChild(username_input);
    username_row.appendChild(username_container);

    return username_row;
};

function createPasswordInput(id: string) {
    const password_row = document.createElement('tr');
    const password_header = document.createElement('th');
    const password_label = document.createElement('label');

    password_label.innerText = 'Password';
    password_label.setAttribute('for', id);
    password_header.appendChild(password_label);
    password_row.appendChild(password_header);
    const password_container = document.createElement('td');
    const password_input = document.createElement('input');

    password_input.type = 'password';
    password_input.id = id;
    password_container.appendChild(password_input);
    password_row.appendChild(password_container);

    return password_row;
};

function createApiTokenInput(id: string) {
    const token_row = document.createElement('tr');
    const token_header = document.createElement('th');
    const token_label = document.createElement('label');

    token_label.innerText = 'API Token';
    token_label.setAttribute('for', id);
    token_header.appendChild(token_label);
    token_row.appendChild(token_header);
    const token_container = document.createElement('td');
    const token_input = document.createElement('input');

    token_input.type = 'text';
    token_input.id = id;
    token_container.appendChild(token_input);
    token_row.appendChild(token_container);

    return token_row;
};

function loadEditTorrent(api_key: string, id: number) {
    const form = document.querySelector('#edit-torrent-form tbody') as HTMLElement;

    form.dataset.id = id.toString();
    form.querySelectorAll(
        'tr:not(:has(input#edit-title-input, input#edit-baseurl-input))',
    ).forEach((el) => {
        el.remove();
    });
    document.querySelector('#test-torrent-edit')?.classList.remove(
        'show-success', 'show-fail',
    );
    hide([document.querySelector('#edit-error')!]);

    fetchAPI(`/externalclients/${id}`, api_key)
        .then((client_data) => {
            const client_type = client_data.result.client_type;

            form.dataset.type = client_type;
            fetchAPI('/externalclients/options', api_key)
                .then((options) => {
                    const client_options = options.result[client_type];

                    (form.querySelector('#edit-title-input') as HTMLInputElement).value = client_data
                        .result.title || '';

                    (form.querySelector('#edit-baseurl-input') as HTMLInputElement).value = client_data
                        .result.base_url;

                    if (client_options.includes('username')) {
                        const username_input = createUsernameInput('edit-username-input');

                        username_input.querySelector('input')!.value = client_data.result.username || '';
                        form.appendChild(username_input);
                    };

                    if (client_options.includes('password')) {
                        const password_input = createPasswordInput('edit-password-input');

                        password_input.querySelector('input')!.value = client_data.result.password || '';
                        form.appendChild(password_input);
                    };

                    if (client_options.includes('api_token')) {
                        const token_input = createApiTokenInput('edit-token-input');

                        token_input.querySelector('input')!.value = client_data.result.api_token || '';
                        form.appendChild(token_input);
                    };

                    WindowFuncs.showWindow('edit-torrent-window');
                });
        });
};

function saveEditTorrent() {
    usingApiKey().then((api_key) => {
        testEditTorrent(api_key).then((result) => {
            if (!result) {
                return;
            }

            const form = document.querySelector('#edit-torrent-form tbody') as HTMLElement;
            const id = form.dataset.id;
            const data = {
                title: (form.querySelector('#edit-title-input') as HTMLInputElement).value,
                base_url: (form.querySelector('#edit-baseurl-input') as HTMLInputElement).value,
                username: (form.querySelector(
                    '#edit-username-input',
                ) as HTMLInputElement)?.value || null,
                password: (form.querySelector(
                    '#edit-password-input',
                ) as HTMLInputElement)?.value || null,
                api_token: (form.querySelector(
                    '#edit-token-input',
                ) as HTMLInputElement)?.value || null,
            };

            sendAPI('PUT', `/externalclients/${id}`, api_key, {}, data)
                .then(() => {
                    loadTorrentClients(api_key);
                    WindowFuncs.closeWindow();
                })
                .catch((e) => {
                    if (e.status === 400) {
                        // Client is downloading
                        const error = document.querySelector('#edit-error') as HTMLElement;

                        error.innerText = '*Client is downloading';
                        hide([], [error]);
                    };
                });
        });
    });
};

async function testEditTorrent(api_key: string) {
    const error = document.querySelector('#edit-error') as HTMLElement;

    hide([error]);
    const form = document.querySelector('#edit-torrent-form tbody') as HTMLElement;
    const test_button = document.querySelector('#test-torrent-edit') as HTMLElement;

    test_button.classList.remove('show-success', 'show-fail');
    const data = {
        client_type: form.dataset.type,
        base_url: (form.querySelector('#edit-baseurl-input') as HTMLInputElement).value,
        username: (form.querySelector('#edit-username-input') as HTMLInputElement)?.value || null,
        password: (form.querySelector('#edit-password-input') as HTMLInputElement)?.value || null,
        api_token: (form.querySelector('#edit-token-input') as HTMLInputElement)?.value || null,
    };

    return await sendAPI('POST', '/externalclients/test', api_key, {}, data)
        .then((response) => response?.json())
        .then((json) => {
            // Test successful
            if (json.result.success) {
                test_button.classList.add('show-success');
            }
            else {
                // Test failed
                test_button.classList.add('show-fail');
                error.innerText = json.result.description;
                hide([], [error]);
            };

            return json.result.success;
        });
};

function deleteTorrent(api_key: string) {
    const id = (document.querySelector('#edit-torrent-form tbody') as HTMLElement).dataset.id;

    sendAPI('DELETE', `/externalclients/${id}`, api_key)
        .then(() => {
            loadTorrentClients(api_key);
            WindowFuncs.closeWindow();
        })
        .catch((e) => {
            if (e.status === 400) {
                // Client is downloading
                const error = document.querySelector('#edit-error') as HTMLElement;

                error.innerText = '*Client is downloading';
                hide([], [error]);
            };
        });
};

function loadTorrentList(api_key: string) {
    const table = document.querySelector('#choose-torrent-list') as HTMLElement;

    table.innerHTML = '';

    fetchAPI('/externalclients/options', api_key).then((json) => {
        Object.keys(json.result).forEach((c) => {
            const entry = document.createElement('button');

            entry.innerText = c;
            entry.onclick = () => loadAddTorrent(api_key, c);
            table.appendChild(entry);
        });
        WindowFuncs.showWindow('choose-torrent-window');
    });
};

function loadAddTorrent(api_key: string, client_type: string) {
    const form = document.querySelector('#add-torrent-form tbody') as HTMLElement;

    form.dataset.type = client_type;

    form.querySelectorAll(
        'tr:not(:has(input#add-title-input, input#add-baseurl-input))',
    ).forEach((el) => {
        el.remove();
    });

    document.querySelector('#test-torrent-add')?.classList.remove(
        'show-success', 'show-fail',
    );

    (form.querySelectorAll(
        '#add-title-input, #add-baseurl-input',
    ) as NodeListOf<HTMLInputElement>).forEach((el) => {
        el.value = '';
    });

    fetchAPI('/externalclients/options', api_key).then((json) => {
        const client_options = json.result[client_type];

        if (client_options.includes('username')) {
            form.appendChild(createUsernameInput('add-username-input'));
        }

        if (client_options.includes('password')) {
            form.appendChild(createPasswordInput('add-password-input'));
        }

        if (client_options.includes('api_token')) {
            form.appendChild(createApiTokenInput('add-token-input'));
        }

        WindowFuncs.showWindow('add-torrent-window');
    });
};

function saveAddTorrent() {
    usingApiKey().then((api_key) => {
        testAddTorrent(api_key).then((result) => {
            if (!result) {
                return;
            }

            const form = document.querySelector('#add-torrent-form tbody') as HTMLElement;
            const data = {
                client_type: form.dataset.type,
                title: (form.querySelector('#add-title-input') as HTMLInputElement).value,
                base_url: (form.querySelector('#add-baseurl-input') as HTMLInputElement).value,
                username: (form.querySelector('#add-username-input') as HTMLInputElement)?.value || null,
                password: (form.querySelector('#add-password-input') as HTMLInputElement)?.value || null,
                api_token: (form.querySelector('#add-token-input') as HTMLInputElement)?.value || null,
            };

            sendAPI('POST', '/externalclients', api_key, {}, data).then(() => {
                loadTorrentClients(api_key);
                WindowFuncs.closeWindow();
            });
        });
    });
};

async function testAddTorrent(api_key: string) {
    const error = document.querySelector('#add-error') as HTMLElement;

    hide([error]);
    const form = document.querySelector('#add-torrent-form tbody') as HTMLElement;
    const test_button = document.querySelector('#test-torrent-add') as HTMLElement;

    test_button.classList.remove('show-success', 'show-fail');

    const data = {
        client_type: form.dataset.type,
        base_url: (form.querySelector('#add-baseurl-input') as HTMLInputElement).value,
        username: (form.querySelector('#add-username-input') as HTMLInputElement)?.value || null,
        password: (form.querySelector('#add-password-input') as HTMLInputElement)?.value || null,
        api_token: (form.querySelector('#add-token-input') as HTMLInputElement)?.value || null,
    };

    return await sendAPI('POST', '/externalclients/test', api_key, {}, data)
        .then((response) => response?.json())
        .then((json) => {
            // Test successful
            if (json.result.success) {
                test_button.classList.add('show-success');
            }
            // Test failed
            else {
                test_button.classList.add('show-fail');
            }
            error.innerText = json.result.description;
            hide([], [error]);

            return json.result.success;
        });
};

function loadTorrentClients(api_key: string) {
    fetchAPI('/externalclients', api_key).then((json) => {
        const table = document.querySelector('#torrent-client-list') as HTMLElement;

        document.querySelectorAll('#torrent-client-list > :not(:first-child)').forEach((el) => {
            el.remove();
        });

        (json.result as ExternalClient[]).forEach((client) => {
            const entry = document.createElement('button');

            entry.onclick = () => loadEditTorrent(api_key, client.id);
            entry.innerText = client.title;
            table.appendChild(entry);
        });
    });
};

function fillCredentials(api_key: string) {
    fetchAPI('/credentials', api_key)
        .then((json) => {
            document.querySelectorAll('#mega-creds, #pixeldrain-creds').forEach(
                (c) => {
                    c.innerHTML = '';
                },
            );
            (json.result as CredentialData[]).forEach((result) => {
                if (result.source === 'mega') {
                    const row = document.querySelector(
                        '.pre-build-els .mega-cred-entry',
                    )?.cloneNode(true) as HTMLElement;

                    (row.querySelector('.mega-email') as HTMLElement).innerText = result.email ?? '';
                    (row.querySelector('.mega-password') as HTMLElement).innerText = result
                        .password ?? '';
                    (row.querySelector('.delete-credential') as HTMLButtonElement).onclick = () => {
                        sendAPI('DELETE', `/credentials/${result.id}`, api_key).then(() => row.remove());
                    };
                    document.querySelector('#mega-creds')?.appendChild(row);
                }
                else if (result.source === 'pixeldrain') {
                    const row = document.querySelector(
                        '.pre-build-els .pixeldrain-cred-entry',
                    )?.cloneNode(true) as HTMLElement;

                    (row.querySelector('.pixeldrain-key') as HTMLElement).innerText = result
                        .api_key ?? '';
                    (row.querySelector('.delete-credential') as HTMLButtonElement).onclick = () => {
                        sendAPI('DELETE', `/credentials/${result.id}`, api_key)
                            .then(() => row.remove());
                    };
                    document.querySelector('#pixeldrain-creds')?.appendChild(row);
                };
            });
        });

    (document.querySelectorAll(
        '#mega-form input, #pixeldrain-form input',
    ) as NodeListOf<HTMLInputElement>).forEach(
        (i) => {
            i.value = '';
        },
    );
};

function addCredential() {
    hide([document.querySelector('#builtin-window p.error')!]);

    const source = (document.querySelector('#builtin-window') as HTMLElement).dataset.tag;
    let data: Record<string, string>;

    if (source === 'mega') {
        data = {
            source,
            email: (document.querySelector('#add-mega .mega-email input') as HTMLInputElement).value,
            password: (document.querySelector(
                '#add-mega .mega-password input',
            ) as HTMLInputElement).value,
        };
    }

    else if (source === 'pixeldrain') {
        data = {
            source,
            api_key: (document.querySelector(
                '#add-pixeldrain .pixeldrain-key input',
            ) as HTMLInputElement).value,
        };
    }

    usingApiKey().then((api_key) => {
        sendAPI('POST', '/credentials', api_key, {}, data)
            .then(() => fillCredentials(api_key))
            .catch((e) => {
                if (e.status === 400) {
                    // eslint-disable-next-line
                    e.json().then((json: any) => {
                        (document.querySelector('#builtin-window p.error') as HTMLElement)
                            .innerText = json.result.description;

                        hide([], [document.querySelector('#builtin-window p.error')!]);
                    });
                }
                else {
                    console.log(e);
                }
            });
    });
};

const toggles = {
    getcomics: document.querySelector('#gc-toggle') as HTMLInputElement,
    libgen: document.querySelector('#lg-toggle') as HTMLInputElement,
};

function fillSettings(api_key: string) {
    fetchAPI('/settings', api_key)
        .then((json) => {
            toggles.getcomics.checked = json.result.enable_getcomics;
            toggles.libgen.checked = json.result.enable_libgen;
        });
};

// code run on load

usingApiKey().then((api_key) => {
    fillSettings(api_key);
    fillCredentials(api_key);
    loadTorrentClients(api_key);

    (document.querySelector(
        '#delete-torrent-edit',
    ) as HTMLInputElement).onclick = () => deleteTorrent(api_key);
    (document.querySelector(
        '#test-torrent-edit',
    ) as HTMLInputElement).onclick = () => testEditTorrent(api_key);
    (document.querySelector(
        '#test-torrent-add',
    ) as HTMLInputElement).onclick = () => testAddTorrent(api_key);
    (document.querySelector(
        '#add-torrent-client',
    ) as HTMLInputElement).onclick = () => loadTorrentList(api_key);

    toggles.getcomics.onchange = () => {
        const data = { enable_getcomics: toggles.getcomics.checked };

        sendAPI('PUT', '/settings', api_key, {}, data);
    };

    toggles.libgen.onchange = () => {
        const data = { enable_libgen: toggles.libgen.checked };

        sendAPI('PUT', '/settings', api_key, {}, data);
    };
});

(document.querySelector(
    '#edit-torrent-form',
) as HTMLFormElement).action = 'javascript:saveEditTorrent()';
(document.querySelector(
    '#add-torrent-form',
) as HTMLFormElement).action = 'javascript:saveAddTorrent()';

(document.querySelectorAll(
    '#cred-container > form',
) as NodeListOf<HTMLFormElement>).forEach(
    (f) => {
        f.action = 'javascript:addCredential();';
    },
);

(document.querySelectorAll(
    '#builtin-client-list > button',
) as NodeListOf<HTMLButtonElement>).forEach((b) => {
    const tag = b.dataset.tag;

    b.onclick = () => {
        (document.querySelector('#builtin-window') as HTMLElement).dataset.tag = tag;

        hide([document.querySelector('#builtin-window p.error')!]);

        (document.querySelectorAll(
            '#builtin-window input',
        ) as NodeListOf<HTMLButtonElement>).forEach((i) => {
            i.value = '';
        });

        WindowFuncs.showWindow('builtin-window');
    };
});

declare global {
    interface Window {
        addCredential: () => void
        saveAddTorrent: () => void
        saveEditTorrent: () => void
    }
}

window.addCredential = addCredential;
window.saveAddTorrent = saveAddTorrent;
window.saveEditTorrent = saveEditTorrent;
