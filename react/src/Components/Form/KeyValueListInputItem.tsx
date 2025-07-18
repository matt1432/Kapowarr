// IMPORTS

// React
import { type JSX, useCallback } from 'react';

// Misc
import { icons } from 'Helpers/Props';

// General Components
import IconButton from 'Components/Link/IconButton';

// Specific Components
import TextInput from './TextInput';

// CSS
import styles from './KeyValueListInputItem.module.css';

// Types
interface KeyValueListInputItemProps {
    index: number;
    keyValue: string;
    value: string;
    keyPlaceholder?: string;
    valuePlaceholder?: string;
    isNew: boolean;
    onChange: (index: number, itemValue: { key: string; value: string }) => void;
    onRemove: (index: number) => void;
    onFocus: () => void;
    onBlur: () => void;
}

// IMPLEMENTATIONS

function KeyValueListInputItem({
    index,
    keyValue,
    value,
    keyPlaceholder = 'Key',
    valuePlaceholder = 'Value',
    isNew,
    onChange,
    onRemove,
    onFocus,
    onBlur,
}: KeyValueListInputItemProps): JSX.Element {
    const handleKeyChange = useCallback(
        ({ value: keyValue }: { value: string }) => {
            onChange(index, { key: keyValue, value });
        },
        [index, value, onChange],
    );

    const handleValueChange = useCallback(
        ({ value }: { value: string }) => {
            onChange(index, { key: keyValue, value });
        },
        [index, keyValue, onChange],
    );

    const handleRemovePress = useCallback(() => {
        onRemove(index);
    }, [index, onRemove]);

    return (
        <div className={styles.itemContainer}>
            <div className={styles.keyInputWrapper}>
                <TextInput
                    className={styles.keyInput}
                    name="key"
                    value={keyValue}
                    placeholder={keyPlaceholder}
                    onChange={handleKeyChange}
                    onFocus={onFocus}
                    onBlur={onBlur}
                />
            </div>

            <div className={styles.valueInputWrapper}>
                <TextInput
                    className={styles.valueInput}
                    name="value"
                    value={value}
                    placeholder={valuePlaceholder}
                    onChange={handleValueChange}
                    onFocus={onFocus}
                    onBlur={onBlur}
                />
            </div>

            <div className={styles.buttonWrapper}>
                {isNew ? null : (
                    <IconButton name={icons.REMOVE} tabIndex={-1} onPress={handleRemovePress} />
                )}
            </div>
        </div>
    );
}

export default KeyValueListInputItem;
