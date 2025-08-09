// IMPORTS

// Misc
import classNames from 'classnames';
import formatBytes from 'Utilities/Number/formatBytes';
import translate from 'Utilities/String/translate';

// Specific Components
import EnhancedSelectInputOption, {
    type EnhancedSelectInputOptionProps,
} from '../EnhancedSelectInputOption';

// CSS
import styles from './index.module.css';

// Types
interface RootFolderSelectInputOptionProps extends EnhancedSelectInputOptionProps {
    id: string;
    value: string;
    freeSpace?: number;
    isMissing?: boolean;
    volumeFolder?: string;
    isMobile: boolean;
    isWindows?: boolean;
}

// IMPLEMENTATIONS

function RootFolderSelectInputOption({
    id,
    value,
    freeSpace,
    isMissing,
    volumeFolder,
    isMobile,
    ...otherProps
}: RootFolderSelectInputOptionProps) {
    return (
        <EnhancedSelectInputOption id={id} isMobile={isMobile} {...otherProps}>
            <div className={classNames(styles.optionText, isMobile && styles.isMobile)}>
                <div className={styles.value}>
                    {value}

                    {volumeFolder && id !== 'addNew' ? (
                        <div className={styles.volumeFolder}>{volumeFolder}</div>
                    ) : null}
                </div>

                {!freeSpace ? null : (
                    <div className={styles.freeSpace}>
                        {translate('RootFolderSelectFreeSpace', {
                            freeSpace: formatBytes(freeSpace),
                        })}
                    </div>
                )}

                {isMissing ? <div className={styles.isMissing}>{translate('Missing')}</div> : null}
            </div>
        </EnhancedSelectInputOption>
    );
}

export default RootFolderSelectInputOption;
