// IMPORTS

// Misc
import classNames from 'classnames';

// Specific Components
import EnhancedSelectInputOption, {
    type EnhancedSelectInputOptionProps,
} from '../EnhancedSelectInputOption';

// CSS
import styles from './index.module.css';

// Types
interface SpecialVersionSelectInputOptionProps extends EnhancedSelectInputOptionProps {
    id: string;
    value: string;
    isMobile: boolean;
}

// IMPLEMENTATIONS

export default function SpecialVersionSelectInputOption({
    id,
    value,
    isMobile,
    ...otherProps
}: SpecialVersionSelectInputOptionProps) {
    return (
        <EnhancedSelectInputOption {...otherProps} id={id} isMobile={isMobile}>
            <div
                className={classNames(
                    styles.optionText,
                    isMobile && styles.isMobile,
                )}
            >
                <div className={styles.value}>{value}</div>
            </div>
        </EnhancedSelectInputOption>
    );
}
