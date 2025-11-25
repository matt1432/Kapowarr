import { icons, sortDirections } from 'Helpers/Props';

import type { TableState } from 'Store/Slices/TableOptions';

export type InteractiveSearchColumnName =
    | 'match'
    | 'issueNumber'
    | 'displayTitle'
    | 'filesize'
    | 'pages'
    | 'releaser'
    | 'scanType'
    | 'resolution'
    | 'dpi'
    | 'source'
    | 'matchRejections'
    | 'actions';

export default {
    hideDownloaded: false,
    hideDownloading: false,
    hideUnmonitored: false,
    hideUnmatched: false,

    sortKey: 'issueNumber',
    sortDirection: sortDirections.DESCENDING,

    secondarySortKey: null,
    secondarySortDirection: null,

    columns: [
        {
            name: 'match',
            isModifiable: false,
            isSortable: true,
            isVisible: true,
        },
        {
            name: 'issueNumber',
            isModifiable: false,
            isSortable: true,
            isVisible: true,
        },
        {
            name: 'displayTitle',
            isModifiable: false,
            isSortable: true,
            isVisible: true,
        },
        {
            name: 'filesize',
            isModifiable: false,
            isSortable: true,
            isVisible: true,
        },
        {
            name: 'pages',
            isModifiable: false,
            isSortable: true,
            isVisible: true,
        },
        {
            name: 'releaser',
            isModifiable: false,
            isSortable: true,
            isVisible: true,
        },
        {
            name: 'scanType',
            isModifiable: false,
            isSortable: true,
            isVisible: true,
        },
        {
            name: 'resolution',
            isModifiable: false,
            isSortable: true,
            isVisible: true,
        },
        {
            name: 'dpi',
            isModifiable: false,
            isSortable: true,
            isVisible: true,
        },
        {
            name: 'source',
            isModifiable: false,
            isSortable: true,
            isVisible: true,
        },
        {
            name: 'matchRejections',
            icon: {
                name: icons.DANGER,
                title: 'Rejections',
            },
            isModifiable: false,
            isSortable: true,
            fixedSortDirection: sortDirections.ASCENDING,
            isVisible: true,
        },
        {
            name: 'actions',
            hideHeaderLabel: true,
            isModifiable: false,
            isSortable: false,
            isVisible: true,
        },
    ],
} satisfies TableState<'interactiveSearch'>;
