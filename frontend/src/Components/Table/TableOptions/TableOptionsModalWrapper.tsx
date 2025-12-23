// IMPORTS

// React
import React, { type ReactElement, useCallback, useState } from 'react';

// Specific Components
import TableOptionsModal from './TableOptionsModal';

// Types
import type { LinkProps } from 'Components/Link/Link';
import type { Column } from '../Column';
import type { ColumnNameMap } from 'Store/Slices/TableOptions';
import type { TableOptionsModalProps } from './TableOptionsModal';

interface TableOptionsModalWrapperProps<
    Name extends keyof ColumnNameMap,
    ColumnName extends ColumnNameMap[Name],
> extends Omit<
    TableOptionsModalProps<Name, ColumnName>,
    'isOpen' | 'onModalClose'
> {
    columns: Column<ColumnName>[];
    children: ReactElement<LinkProps>;
}

// IMPLEMENTATIONS

export default function TableOptionsModalWrapper<
    Name extends keyof ColumnNameMap,
    ColumnName extends ColumnNameMap[Name],
>({
    columns,
    children,
    ...otherProps
}: TableOptionsModalWrapperProps<Name, ColumnName>) {
    const [isTableOptionsModalOpen, setIsTableOptionsModalOpen] =
        useState(false);

    const handleTableOptionsPress = useCallback(() => {
        setIsTableOptionsModalOpen(true);
    }, []);

    const handleTableOptionsModalClose = useCallback(() => {
        setIsTableOptionsModalOpen(false);
    }, []);

    return (
        <>
            {React.isValidElement(children)
                ? React.cloneElement(children, {
                      onPress: handleTableOptionsPress,
                  })
                : null}

            <TableOptionsModal
                {...otherProps}
                isOpen={isTableOptionsModalOpen}
                columns={columns}
                onModalClose={handleTableOptionsModalClose}
            />
        </>
    );
}
