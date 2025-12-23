// IMPORTS

// React
import React from 'react';

// Misc
import classNames from 'classnames';

// Specific Components
import EnhancedSelectInputOption, {
    type EnhancedSelectInputOptionProps,
} from '../EnhancedSelectInputOption';

// CSS
import styles from './index.module.css';

// Types
interface HintedSelectInputOptionProps extends Omit<
    EnhancedSelectInputOptionProps,
    'isSelected'
> {
    value: string;
    hint?: React.ReactNode;
    isSelected?: boolean;
}

// IMPLEMENTATIONS

export default function HintedSelectInputOption({
    id,
    value,
    hint,
    depth,
    isSelected = false,
    isMobile,
    ...otherProps
}: HintedSelectInputOptionProps) {
    return (
        <EnhancedSelectInputOption
            id={id}
            depth={depth}
            isSelected={isSelected}
            isMobile={isMobile}
            {...otherProps}
        >
            <div
                className={classNames(
                    styles.optionText,
                    isMobile && styles.isMobile,
                )}
            >
                <div>{value}</div>

                {hint && <div className={styles.hintText}>{hint}</div>}
            </div>
        </EnhancedSelectInputOption>
    );
}
