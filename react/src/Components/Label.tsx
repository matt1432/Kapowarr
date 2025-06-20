import classNames from 'classnames';
import { type ComponentProps, type ReactNode } from 'react';
import { kinds, sizes } from 'Helpers/Props';
import { type Kind } from 'Helpers/Props/kinds';
import { type Size } from 'Helpers/Props/sizes';
import styles from './Label.css';

export interface LabelProps extends ComponentProps<'span'> {
    kind?: Extract<Kind, keyof typeof styles>;
    size?: Extract<Size, keyof typeof styles>;
    outline?: boolean;
    children: ReactNode;
}

export default function Label({
    className = styles.label,
    kind = kinds.DEFAULT,
    size = sizes.SMALL,
    outline = false,
    ...otherProps
}: LabelProps) {
    return (
        <span
            className={classNames(className, styles[kind], styles[size], outline && styles.outline)}
            {...otherProps}
        />
    );
}
