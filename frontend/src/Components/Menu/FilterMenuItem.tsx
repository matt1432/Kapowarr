// IMPORTS

// React
import React from 'react';

// Specific Components
import SelectedMenuItem, {
    type SelectedMenuItemProps,
} from './SelectedMenuItem';

// Types
interface FilterMenuItemProps<T extends string> extends Omit<
    SelectedMenuItemProps<T>,
    'isSelected' | 'onPress'
> {
    name?: T;
    filterKey: T;
    children: React.ReactNode;
    onPress: (view: T) => void;
}

// IMPLEMENTATIONS

export default function FilterMenuItem<T extends string>({
    name,
    filterKey,
    ...otherProps
}: FilterMenuItemProps<T>) {
    const isSelected = name === filterKey;

    return (
        <SelectedMenuItem name={name} isSelected={isSelected} {...otherProps} />
    );
}
