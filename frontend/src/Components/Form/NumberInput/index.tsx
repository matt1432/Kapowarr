// IMPORTS

// React
import { useCallback, useState } from 'react';

// Specific Components
import TextInput from '../TextInput';

// Types
import type { InputChanged } from 'typings/Inputs';
import type { TextInputProps } from '../TextInput';

export interface NumberInputProps<K extends string> extends Omit<
    TextInputProps<K, 'number'>,
    'value' | 'onChange'
> {
    value?: number | null;
    min?: number;
    max?: number;
    isFloat?: boolean;
    onChange: (input: InputChanged<K, number | null>) => void;
}

// IMPLEMENTATIONS

function parseValue(
    value: string | null | undefined,
    isFloat: boolean,
    min: number | undefined,
    max: number | undefined,
) {
    if (!value || value === '') {
        return null;
    }

    let newValue = isFloat ? parseFloat(value) : parseInt(value);

    if (min && newValue !== null && newValue < min) {
        newValue = min;
    }
    else if (max && newValue !== null && newValue > max) {
        newValue = max;
    }

    return newValue;
}

export default function NumberInput<K extends string>({
    name,
    value: inputValue = null,
    isFloat = false,
    min,
    max,
    onChange,
    ...otherProps
}: NumberInputProps<K>) {
    const [value, setValue] = useState(
        inputValue === null ? '' : inputValue.toString(),
    );
    const [isFocused, setIsFocused] = useState(false);

    const handleChange = useCallback(
        ({ name, value: newValue }: InputChanged<K, string>) => {
            setValue(newValue);

            onChange({
                name,
                value: parseValue(newValue, isFloat, min, max),
            });
        },
        [isFloat, min, max, onChange, setValue],
    );

    const handleFocus = useCallback(() => {
        setIsFocused(true);
    }, []);

    const handleBlur = useCallback(() => {
        const parsedValue = parseValue(value, isFloat, min, max);
        const stringValue = parsedValue === null ? '' : parsedValue.toString();

        if (stringValue !== value) {
            setValue(stringValue);
        }

        onChange({
            name,
            value: parsedValue,
        });

        setIsFocused(false);
    }, [name, value, isFloat, min, max, onChange]);

    const [prevValue, setPrevValue] = useState<string | number | null>(value);
    const [prevInputValue, setPrevInputValue] = useState<
        string | number | null
    >(inputValue);
    if (prevInputValue !== inputValue || value !== prevValue) {
        setPrevValue(value);
        setPrevInputValue(inputValue);

        if (inputValue === null) {
            setValue('');
        }
        else if (
            !isNaN(inputValue) &&
            inputValue !== prevValue &&
            !isFocused
        ) {
            setValue(inputValue === null ? '' : inputValue.toString());
        }
    }

    return (
        <TextInput
            {...otherProps}
            name={name}
            type="number"
            value={value === null ? '' : value}
            min={min}
            max={max}
            onChange={handleChange}
            onBlur={handleBlur}
            onFocus={handleFocus}
        />
    );
}
