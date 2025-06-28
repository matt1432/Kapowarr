import { type SyntheticEvent } from 'react';
import { type IconName } from 'Components/Icon';
import MenuItem from 'Components/Menu/MenuItem';
import SpinnerIcon from 'Components/SpinnerIcon';
import styles from './PageToolbarOverflowMenuItem.module.css';

interface PageToolbarOverflowMenuItemProps {
    iconName: IconName;
    spinningName?: IconName;
    isDisabled?: boolean;
    isSpinning?: boolean;
    showIndicator?: boolean;
    label: string;
    text?: string;
    onPress?: (event: SyntheticEvent<Element, Event>) => void;
}

function PageToolbarOverflowMenuItem(props: PageToolbarOverflowMenuItemProps) {
    const { iconName, spinningName, label, isDisabled, isSpinning = false, ...otherProps } = props;

    return (
        <MenuItem key={label} isDisabled={isDisabled || isSpinning} {...otherProps}>
            <SpinnerIcon
                className={styles.icon}
                name={iconName}
                spinningName={spinningName}
                isSpinning={isSpinning}
            />
            {label}
        </MenuItem>
    );
}

export default PageToolbarOverflowMenuItem;
