// IMPORTS

// Misc
import { icons } from 'Helpers/Props';

import classNames from 'classnames';

// General Components
import Icon, { type IconName } from 'Components/Icon';
import MenuButton, { type MenuButtonProps } from 'Components/Menu/MenuButton';

// CSS
import styles from './index.module.css';

// Types
export interface ToolbarMenuButtonProps extends Omit<
    MenuButtonProps,
    'children'
> {
    className?: string;
    iconName: IconName;
    showIndicator?: boolean;
    text?: string;
}

// IMPLEMENTATIONS

export default function ToolbarMenuButton({
    iconName,
    showIndicator = false,
    text,
    ...otherProps
}: ToolbarMenuButtonProps) {
    return (
        <MenuButton className={styles.menuButton} {...otherProps}>
            <div>
                <Icon name={iconName} size={21} />

                {showIndicator ? (
                    <span
                        className={classNames(
                            styles.indicatorContainer,
                            'fa-layers fa-fw',
                        )}
                    >
                        <Icon name={icons.CIRCLE} size={9} />
                    </span>
                ) : null}

                <div className={styles.labelContainer}>
                    <div className={styles.label}>{text}</div>
                </div>
            </div>
        </MenuButton>
    );
}
