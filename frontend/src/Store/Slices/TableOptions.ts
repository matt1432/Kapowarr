// IMPORTS

// Redux
import { createSlice, type PayloadAction } from '@reduxjs/toolkit';

// Misc
import { sortDirections } from 'Helpers/Props';

// Types
import type { EmptyObject } from 'type-fest';

import type { Column } from 'Components/Table/Column';
import type { SortDirection } from 'Helpers/Props/sortDirections';

// Columns
import blocklistTable, {
    type BlocklistColumnName,
} from 'Activity/Blocklist/columns';

import changeMatch, {
    type ChangeMatchColumnName,
} from 'AddVolume/ImportVolume/ImportProposals/ChangeMatch/columns';

import credentialTable, {
    type CredentialColumnName,
} from 'Settings/DownloadClientSettings/BuiltInClients/CredentialTable/columns';

import folderTable, {
    type FolderTableColumnName,
} from 'AddVolume/ImportVolume/ImportForm/FolderTable/columns';

import generalFiles, {
    type GeneralFilesColumnName,
} from 'Volume/GeneralFiles/columns';

import historyTable, { type HistoryColumnName } from 'History/columns';

import importProposals, {
    type ProposalColumnName,
} from 'AddVolume/ImportVolume/ImportProposals/columns';

import issueSummary, {
    type IssueSummaryColumnName,
} from 'Issue/Summary/columns';

import issueTable, {
    type IssueColumnName,
} from 'Volume/Details/IssueTable/columns';

import queueTable, { type QueueColumnName } from 'Activity/Queue/columns';

import rootFolders, {
    type RootFolderColumnName,
} from 'Settings/MediaManagement/RootFolders/columns';

import interactiveSearch, {
    type InteractiveSearchColumnName,
} from 'InteractiveSearch/columns';

import taskHistory, {
    type TaskHistoryColumnName,
} from 'System/Tasks/History/columns';

import taskPlanning, {
    type TaskPlanningColumnName,
} from 'System/Tasks/Scheduled/columns';

import volumeIndex, { type VolumeIndexColumnName } from 'Volume/Index/columns';

export interface ColumnNameMap {
    blocklistTable: BlocklistColumnName;
    changeMatch: ChangeMatchColumnName;
    credentialTable: CredentialColumnName;
    folderTable: FolderTableColumnName;
    generalFiles: GeneralFilesColumnName;
    historyTable: HistoryColumnName;
    importProposals: ProposalColumnName;
    interactiveSearch: InteractiveSearchColumnName;
    issueSummary: IssueSummaryColumnName;
    issueTable: IssueColumnName;
    queueTable: QueueColumnName;
    rootFolders: RootFolderColumnName;
    taskHistory: TaskHistoryColumnName;
    taskPlanning: TaskPlanningColumnName;
    volumeIndex: VolumeIndexColumnName;
}

interface _ExtraPropsMap {
    interactiveSearch: {
        hideDownloaded: boolean;
        hideDownloading: boolean;
        hideUnmonitored: boolean;
        hideUnmatched: boolean;
    };
}

export type ExtraPropsMap = {
    [Key in Exclude<keyof ColumnNameMap, keyof _ExtraPropsMap>]: EmptyObject;
} & _ExtraPropsMap;

export interface SetTableSortParams<Name extends keyof ColumnNameMap> {
    tableName: Name;
    sortKey: ColumnNameMap[Name];
    sortDirection?: SortDirection | null;
}

export type SetTableOptionsParams<
    Name extends keyof ColumnNameMap,
    ExtraProps extends ExtraPropsMap[Name] = ExtraPropsMap[Name],
> = {
    tableName: Name;
    columns?: Column<ColumnNameMap[Name]>[];
} & Partial<ExtraProps>;

export type TableState<
    Name extends keyof ColumnNameMap,
    ExtraProps extends ExtraPropsMap[Name] = ExtraPropsMap[Name],
> = {
    sortKey: ColumnNameMap[Name] | null;
    sortDirection: SortDirection | null;
    secondarySortKey: ColumnNameMap[Name] | null;
    secondarySortDirection: SortDirection | null;
    columns: Column<ColumnNameMap[Name]>[];
} & ExtraProps;

export interface TableOptionsState {
    sliceVersion: number;

    blocklistTable: TableState<'blocklistTable'>;
    changeMatch: TableState<'changeMatch'>;
    credentialTable: TableState<'credentialTable'>;
    folderTable: TableState<'folderTable'>;
    generalFiles: TableState<'generalFiles'>;
    historyTable: TableState<'historyTable'>;
    importProposals: TableState<'importProposals'>;
    interactiveSearch: TableState<'interactiveSearch'>;
    issueSummary: TableState<'issueSummary'>;
    issueTable: TableState<'issueTable'>;
    queueTable: TableState<'queueTable'>;
    rootFolders: TableState<'rootFolders'>;
    taskHistory: TableState<'taskHistory'>;
    taskPlanning: TableState<'taskPlanning'>;
    volumeIndex: TableState<'volumeIndex'>;
}

// IMPLEMENTATIONS

const initialState = {
    sliceVersion: 4,

    blocklistTable,
    changeMatch,
    credentialTable,
    folderTable,
    generalFiles,
    historyTable,
    importProposals,
    interactiveSearch,
    issueSummary,
    issueTable,
    queueTable,
    rootFolders,
    taskHistory,
    taskPlanning,
    volumeIndex,
} satisfies TableOptionsState as TableOptionsState;

const TableOptionsSlice = createSlice({
    name: 'tableOptions',
    initialState,
    reducers: {
        setTableSort: <Name extends keyof ColumnNameMap>(
            state: TableOptionsState,
            {
                payload: { tableName, sortKey, sortDirection = null },
            }: PayloadAction<SetTableSortParams<Name>>,
        ) => {
            const currentState = state[tableName];

            if (currentState.sortKey === sortKey) {
                if (sortDirection) {
                    state[tableName].sortDirection = sortDirection;
                }
                else {
                    // cycle sortDirection
                    switch (currentState.sortDirection) {
                        case sortDirections.DESCENDING: {
                            state[tableName].sortKey = null;
                            state[tableName].sortDirection = null;
                            break;
                        }
                        case sortDirections.ASCENDING: {
                            state[tableName].sortDirection =
                                sortDirections.DESCENDING;
                            break;
                        }
                        case null: {
                            state[tableName].sortDirection =
                                sortDirections.ASCENDING;
                            break;
                        }
                    }
                }
            }
            else if (currentState.secondarySortKey === sortKey) {
                if (sortDirection) {
                    state[tableName].secondarySortDirection = sortDirection;
                }
                else {
                    // cycle secondarySortDirection
                    switch (currentState.secondarySortDirection) {
                        case sortDirections.DESCENDING: {
                            state[tableName].secondarySortKey = null;
                            state[tableName].secondarySortDirection = null;
                            break;
                        }
                        case sortDirections.ASCENDING: {
                            state[tableName].secondarySortDirection =
                                sortDirections.DESCENDING;
                            break;
                        }
                        case null: {
                            state[tableName].secondarySortDirection =
                                sortDirections.ASCENDING;
                            break;
                        }
                    }
                }
            }
            else if (currentState.sortKey === null) {
                // init sortKey
                state[tableName].sortKey = sortKey;
                state[tableName].sortDirection =
                    sortDirection ?? sortDirections.ASCENDING;
            }
            else {
                // init secondarySortKey
                state[tableName].secondarySortKey = sortKey;
                state[tableName].secondarySortDirection =
                    sortDirection ?? sortDirections.ASCENDING;
            }
        },

        setTableOptions: <Name extends keyof ColumnNameMap>(
            state: TableOptionsState,
            {
                payload: { tableName, ...options },
            }: PayloadAction<SetTableOptionsParams<Name>>,
        ) => {
            const newState = { ...state[tableName] };
            state[tableName] = Object.assign(newState, options);
        },
    },
});

// This fixes generic types
export const setTableSort = <Name extends keyof ColumnNameMap>(
    payload: SetTableSortParams<Name>,
) => TableOptionsSlice.actions.setTableSort(payload);

export const setTableOptions = <Name extends keyof ColumnNameMap>(
    payload: SetTableOptionsParams<Name>,
) => TableOptionsSlice.actions.setTableOptions(payload);

export default TableOptionsSlice;
