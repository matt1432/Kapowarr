// IMPORTS

// React
import React from 'react';

// Specific Components
import SelectedMenuItem, {
    type SelectedMenuItemProps,
} from './SelectedMenuItem';

// Types
import type { IndexView } from 'Volume/Index';

interface ViewMenuItemProps extends Omit<
    SelectedMenuItemProps<IndexView>,
    'isSelected'
> {
    name?: IndexView;
    selectedView: IndexView;
    children: React.ReactNode;
    onPress: (view: IndexView) => void;
}

// IMPLEMENTATIONS

export default function ViewMenuItem({
    name,
    selectedView,
    ...otherProps
}: ViewMenuItemProps) {
    const isSelected = name === selectedView;

    return (
        <SelectedMenuItem name={name} isSelected={isSelected} {...otherProps} />
    );
}
