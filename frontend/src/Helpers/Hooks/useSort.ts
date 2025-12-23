// IMPORTS

// React
import { useMemo, type RefObject } from 'react';

// Misc
import { sortDirections } from 'Helpers/Props';

// Types
import type { Column } from 'Components/Table/Column';
import type { SortDirection } from 'Helpers/Props/sortDirections';
import type { ExtendableRecord } from 'typings/Misc';
import type { ColumnNameMap } from 'Store/Slices/TableOptions';

export type Predicates<
    Name extends keyof ColumnNameMap,
    ColumnName extends ColumnNameMap[Name],
    T extends Item<Name, Exclude<ColumnName, 'actions'>> = Item<
        Name,
        Exclude<ColumnName, 'actions'>
    >,
> = Partial<Record<ColumnName, (a: T, b: T) => number>>;

export type Item<
    Name extends keyof ColumnNameMap,
    ColumnName extends ColumnNameMap[Name],
> = ExtendableRecord<ColumnName>;

interface UseSortProps<
    Name extends keyof ColumnNameMap,
    ColumnName extends ColumnNameMap[Name],
    T extends Item<Name, Exclude<ColumnName, 'actions'>> = Item<
        Name,
        Exclude<ColumnName, 'actions'>
    >,
> {
    columns: Column<ColumnName>[];
    items: T[];
    itemsRef?: RefObject<T[]>;

    predicates?: Predicates<Name, ColumnName, T>;

    sortKey?: ColumnName | null;
    sortDirection?: SortDirection | null;
    secondarySortKey?: ColumnName | null;
    secondarySortDirection?: SortDirection | null;
}

// IMPLEMENTATIONS

function predicatesToSorters<
    Name extends keyof ColumnNameMap,
    ColumnName extends ColumnNameMap[Name],
    T extends Item<Name, Exclude<ColumnName, 'actions'>> = Item<
        Name,
        Exclude<ColumnName, 'actions'>
    >,
>(columns: Column<ColumnName>[], predicates: Predicates<Name, ColumnName, T>) {
    const predicateKeys = Object.keys(predicates);
    const missingSortableColumns = columns
        .filter((c) => c.isSortable && !predicateKeys.includes(c.name))
        .map((c) => c.name) as Exclude<ColumnName, 'actions'>[];

    const defaultPredicates = missingSortableColumns.map((key) => [
        key,
        (a: T, b: T) => {
            const aIsNull = typeof a[key] === 'undefined' || a[key] === null;
            const bIsNull = typeof b[key] === 'undefined' || b[key] === null;

            if (aIsNull && bIsNull) {
                return 0;
            }
            else if (aIsNull && !bIsNull) {
                return -1;
            }
            else if (bIsNull && !aIsNull) {
                return 1;
            }

            switch (typeof a[key]) {
                case 'number': {
                    return a[key] - b[key];
                }
                case 'string': {
                    return a[key].localeCompare(b[key]);
                }
                case 'boolean': {
                    return Number(a[key]) - Number(b[key]);
                }
                default: {
                    throw new TypeError(
                        `Property '${key}' is a complex type and cannot be sorted with the default predicates`,
                    );
                }
            }
        },
    ]);
    return Object.fromEntries(
        (
            [...Object.entries(predicates), ...defaultPredicates] as [
                ColumnName,
                (a: T, b: T) => number,
            ][]
        ).map(([key, func]) => [
            key,
            (sortDirection: SortDirection) => {
                return (a: T, b: T) =>
                    sortDirection === sortDirections.ASCENDING
                        ? func(a, b)
                        : func(b, a);
            },
        ]),
    ) as Partial<
        Record<
            ColumnName,
            (sortDirection: SortDirection) => (a: T, b: T) => number
        >
    >;
}

export default function useSort<
    Name extends keyof ColumnNameMap,
    ColumnName extends ColumnNameMap[Name],
    T extends Item<Name, Exclude<ColumnName, 'actions'>> = Item<
        Name,
        Exclude<ColumnName, 'actions'>
    >,
>({
    columns,
    items,
    itemsRef,
    predicates = {},
    sortKey,
    sortDirection = sortDirections.ASCENDING,
    secondarySortKey,
    secondarySortDirection,
}: UseSortProps<Name, ColumnName, T>) {
    const sorters = useMemo(
        () => predicatesToSorters(columns, predicates),
        [columns, predicates],
    );

    return useMemo(() => {
        const finalItems = items.toSorted(
            (a, b) =>
                (sorters[sortKey]?.(sortDirection ?? sortDirections.ASCENDING)(
                    a,
                    b,
                ) ||
                    sorters[secondarySortKey]?.(
                        secondarySortDirection ?? sortDirections.ASCENDING,
                    )(a, b)) ??
                0,
        );
        if (itemsRef) {
            // eslint-disable-next-line react-hooks/refs
            itemsRef.current = finalItems;
        }
        return finalItems;
    }, [
        items,
        itemsRef,
        sorters,
        sortKey,
        sortDirection,
        secondarySortKey,
        secondarySortDirection,
    ]);
}
