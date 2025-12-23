// IMPORTS

// React
import {
    type ChangeEvent,
    type ComponentProps,
    type SyntheticEvent,
    useCallback,
} from 'react';

// Misc
import classNames from 'classnames';

// CSS
import styles from './index.module.css';

// Types
import type { InputChanged } from 'typings/Inputs';

export interface SelectInputOption extends Pick<
    ComponentProps<'option'>,
    'disabled'
> {
    key: string | number;
    value: string | number | (() => string | number);
}

interface SelectInputProps<K extends string, T> {
    className?: string;
    disabledClassName?: string;
    name: K;
    value: string | number;
    values: SelectInputOption[];
    isDisabled?: boolean;
    hasError?: boolean;
    hasWarning?: boolean;
    autoFocus?: boolean;
    onChange: (change: InputChanged<K, T>) => void;
    onBlur?: (event: SyntheticEvent) => void;
}

// IMPLEMENTATIONS

export default function SelectInput<K extends string, T>({
    className = styles.select,
    disabledClassName = styles.isDisabled,
    name,
    value,
    values,
    isDisabled = false,
    hasError,
    hasWarning,
    autoFocus = false,
    onBlur,
    onChange,
}: SelectInputProps<K, T>) {
    const handleChange = useCallback(
        (event: ChangeEvent<HTMLSelectElement>) => {
            onChange({
                name,
                value: event.target.value as T,
            });
        },
        [name, onChange],
    );

    return (
        <select
            className={classNames(
                className,
                hasError && styles.hasError,
                hasWarning && styles.hasWarning,
                isDisabled && disabledClassName,
            )}
            disabled={isDisabled}
            name={name}
            value={value}
            autoFocus={autoFocus}
            onChange={handleChange}
            onBlur={onBlur}
        >
            {values.map((option) => {
                const { key, value: optionValue, ...otherOptionProps } = option;

                return (
                    <option key={key} value={key} {...otherOptionProps}>
                        {typeof optionValue === 'function'
                            ? optionValue()
                            : optionValue}
                    </option>
                );
            })}
        </select>
    );
}
