// IMPORTS

// Redux
import { useRootSelector } from 'Store/createAppStore';

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

import type { ColumnNameMap } from 'Store/Slices/TableOptions';

interface SortedTableProps<
    Name extends keyof ColumnNameMap,
    ColumnName extends ColumnNameMap[Name],
    T extends Item<Name, ColumnName> = Item<Name, ColumnName>,
> {
    tableName: Name;
    columns: Column<ColumnName>[];
    items: T[];
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
    T extends Item<Name, ColumnName> = Item<Name, ColumnName>,
>({
    tableName,
    columns,
    items,
    itemRenderer,
    predicates = {},
    onSortPress,
    tableProps,
}: SortedTableProps<Name, ColumnName, T>) {
    const { sortKey, sortDirection, secondarySortKey, secondarySortDirection } =
        useRootSelector((state) => state.tableOptions[tableName]);

    const sortedItems = useSort({
        columns,
        items,
        predicates,
        sortKey: sortKey as ColumnName | null,
        sortDirection,
        secondarySortKey: secondarySortKey as ColumnName | null,
        secondarySortDirection,
    });

    return (
        <Table
            tableName={tableName}
            columns={columns}
            sortKey={sortKey as ColumnName | null}
            sortDirection={sortDirection}
            secondarySortKey={secondarySortKey as ColumnName | null}
            secondarySortDirection={secondarySortDirection}
            onSortPress={onSortPress}
            {...tableProps}
        >
            <TableBody>{sortedItems.map(itemRenderer)}</TableBody>
        </Table>
    );
}
