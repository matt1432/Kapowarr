// IMPORTS

// Misc
import monitorNewItemsOptions from 'Utilities/Volume/monitorNewItemsOptions';

// Specific Components
import EnhancedSelectInput, {
    type EnhancedSelectInputProps,
    type EnhancedSelectInputValue,
} from '../EnhancedSelectInput';

// Types
export interface MonitorNewItemsSelectInputProps<K extends string> extends Omit<
    EnhancedSelectInputProps<K, EnhancedSelectInputValue<string>, string>,
    'values'
> {
    includeNoChange?: boolean;
    includeNoChangeDisabled?: boolean;
    includeMixed?: boolean;
}

// IMPLEMENTATIONS

export default function MonitorNewItemsSelectInput<K extends string>({
    includeNoChange = false,
    includeNoChangeDisabled = true,
    includeMixed = false,
    ...otherProps
}: MonitorNewItemsSelectInputProps<K>) {
    const values: EnhancedSelectInputValue<string>[] = [
        ...monitorNewItemsOptions,
    ];

    if (includeNoChange) {
        values.unshift({
            key: 'noChange',
            value: 'No Change',
            isDisabled: includeNoChangeDisabled,
        });
    }

    if (includeMixed) {
        values.unshift({
            key: 'mixed',
            value: '(Mixed)',
            isDisabled: true,
        });
    }

    return <EnhancedSelectInput {...otherProps} values={values} />;
}
