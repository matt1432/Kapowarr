// IMPORTS

// Misc
import classNames from 'classnames';
import translate from 'Utilities/String/translate';

// General Components
import Icon, { type IconProps } from 'Components/Icon';

// Specific Components
import Link, { type LinkProps } from '../Link';

// CSS
import styles from './index.module.css';

// Types
export interface IconButtonProps
    extends
        Omit<LinkProps, 'name' | 'kind'>,
        Pick<IconProps, 'name' | 'kind' | 'size' | 'isSpinning'> {
    iconClassName?: IconProps['className'];
}

// IMPLEMENTATIONS

export default function IconButton({
    className = styles.button,
    iconClassName,
    name,
    kind,
    size = 12,
    isSpinning,
    ...otherProps
}: IconButtonProps) {
    return (
        <Link
            className={classNames(
                className,
                otherProps.isDisabled && styles.isDisabled,
            )}
            aria-label={translate('TableOptionsButton')}
            {...otherProps}
        >
            <Icon
                className={iconClassName}
                name={name}
                kind={kind}
                size={size}
                isSpinning={isSpinning}
            />
        </Link>
    );
}
