// IMPORTS

// Misc
import { kinds } from 'Helpers/Props';
import {
    FontAwesomeIcon,
    type FontAwesomeIconProps,
} from '@fortawesome/react-fontawesome';

import classNames from 'classnames';

// CSS
import styles from './index.module.css';

// Types
import type { ComponentProps } from 'react';
import type { Kind } from 'Helpers/Props/kinds';

export type IconName = FontAwesomeIconProps['icon'];
export type IconKind = Extract<Kind, keyof typeof styles>;

export interface IconProps extends Omit<
    FontAwesomeIconProps,
    'icon' | 'spin' | 'name' | 'title' | 'size'
> {
    containerClassName?: ComponentProps<'span'>['className'];
    name: IconName;
    kind?: IconKind;
    size?: number;
    isSpinning?: FontAwesomeIconProps['spin'];
    title?: string | (() => string) | null;
}

// IMPLEMENTATIONS

export default function Icon({
    containerClassName,
    className,
    name,
    kind = kinds.DEFAULT_KIND,
    size = 14,
    title,
    isSpinning = false,
    fixedWidth = false,
    ...otherProps
}: IconProps) {
    const icon = (
        <FontAwesomeIcon
            className={classNames(className, styles[kind])}
            icon={name}
            spin={isSpinning}
            fixedWidth={fixedWidth}
            style={{
                fontSize: `${size}px`,
            }}
            {...otherProps}
        />
    );

    if (title) {
        return (
            <span
                className={containerClassName}
                title={typeof title === 'function' ? title() : title}
            >
                {icon}
            </span>
        );
    }

    return icon;
}
