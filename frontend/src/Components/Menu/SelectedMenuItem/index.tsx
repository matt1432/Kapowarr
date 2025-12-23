// IMPORTS

// React
import React, { useCallback } from 'react';

// Redux

// Misc
import { icons } from 'Helpers/Props';

// General Components
import Icon, { type IconName } from 'Components/Icon';

// Specific Components
import MenuItem, { type MenuItemProps } from '../MenuItem';

// CSS
import styles from './index.module.css';

// Types
export interface SelectedMenuItemProps<T> extends Omit<
    MenuItemProps,
    'onPress' | 'name'
> {
    name?: T;
    children: React.ReactNode;
    selectedIconName?: IconName;
    isSelected: boolean;
    onPress: (name: T) => void;
}

// IMPLEMENTATIONS

export default function SelectedMenuItem<T>({
    children,
    name,
    selectedIconName = icons.CHECK,
    isSelected,
    onPress,
    ...otherProps
}: SelectedMenuItemProps<T>) {
    const handlePress = useCallback(() => {
        onPress(name ?? ('' as T));
    }, [name, onPress]);

    return (
        <MenuItem {...otherProps} onPress={handlePress}>
            <div className={styles.item}>
                {children}

                <Icon
                    className={
                        isSelected ? styles.isSelected : styles.isNotSelected
                    }
                    name={selectedIconName}
                />
            </div>
        </MenuItem>
    );
}
