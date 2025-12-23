// IMPORTS

// React
import { useCallback, useMemo, type RefObject } from 'react';

// Redux
import { useRootDispatch, useRootSelector } from 'Store/createAppStore';
import { setTableOptions, setTableSort } from 'Store/Slices/TableOptions';

// Hooks
import useSort from 'Helpers/Hooks/useSort';

// Specific Components
import Table from './Table';
import TableBody from './TableBody';

// Types
import type { Column } from './Column';
import type { TableProps } from './Table';

import type { Item, Predicates } from 'Helpers/Hooks/useSort';
import type { SortDirection } from 'Helpers/Props/sortDirections';

import type {
    ColumnNameMap,
    SetTableOptionsParams,
} from 'Store/Slices/TableOptions';

interface SortedTableProps<
    Name extends keyof ColumnNameMap,
    ColumnName extends ColumnNameMap[Name],
    T extends Item<Name, Exclude<ColumnName, 'actions'>> = Item<
        Name,
        Exclude<ColumnName, 'actions'>
    >,
> {
    tableName: Name;
    columns: Column<ColumnName>[];
    items: T[];
    itemsRef?: RefObject<T[]>;
    itemRenderer: (item: T) => React.ReactElement;

    predicates?: Predicates<Name, ColumnName, T>;

    onSortPress?: (name: ColumnName, sortDirection?: SortDirection) => void;

    tableProps?: Omit<
        TableProps<Name, ColumnName>,
        | 'children'
        | 'columns'
        | 'onSortPress'
        | 'sortDirection'
        | 'sortKey'
        | 'tableName'
    >;
}

// IMPLEMENTATIONS

export default function SortedTable<
    Name extends keyof ColumnNameMap,
    ColumnName extends ColumnNameMap[Name],
    T extends Item<Name, Exclude<ColumnName, 'actions'>> = Item<
        Name,
        Exclude<ColumnName, 'actions'>
    >,
>({
    tableName,
    columns,
    items,
    itemsRef,
    itemRenderer,
    predicates = {},
    onSortPress,
    tableProps,
}: SortedTableProps<Name, ColumnName, T>) {
    const dispatch = useRootDispatch();

    const { sortKey, sortDirection, secondarySortKey, secondarySortDirection } =
        useRootSelector((state) => state.tableOptions[tableName]);

    const sortedItems = useSort({
        columns,
        items,
        itemsRef,
        predicates,
        sortKey: sortKey as ColumnName | null,
        sortDirection,
        secondarySortKey: secondarySortKey as ColumnName | null,
        secondarySortDirection,
    });

    const handleSortPress = useCallback(
        (name: ColumnName, sortDirection?: SortDirection) => {
            onSortPress?.(name, sortDirection);
            dispatch(setTableSort({ tableName, sortKey: name, sortDirection }));
        },
        [dispatch, onSortPress, tableName],
    );

    const hasOptions = useMemo(
        () =>
            columns.filter((col) => col.isModifiable).length !== 0 ||
            tableProps?.optionsComponent,
        [columns, tableProps],
    );

    const handleTableOptionChange = useCallback(
        (payload: SetTableOptionsParams<Name>) => {
            dispatch(setTableOptions(payload));
        },
        [dispatch],
    );

    return (
        <Table
            tableName={tableName}
            columns={columns}
            sortKey={sortKey as ColumnName | null}
            sortDirection={sortDirection}
            secondarySortKey={secondarySortKey as ColumnName | null}
            secondarySortDirection={secondarySortDirection}
            onSortPress={handleSortPress}
            onTableOptionChange={
                hasOptions ? handleTableOptionChange : undefined
            }
            {...tableProps}
        >
            <TableBody>{sortedItems.map(itemRenderer)}</TableBody>
        </Table>
    );
}
