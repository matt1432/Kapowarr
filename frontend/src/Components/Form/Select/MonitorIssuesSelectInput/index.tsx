// IMPORTS

// Misc
import monitorOptions from 'Utilities/Volume/monitorOptions';
import translate from 'Utilities/String/translate';

// Specific Components
import EnhancedSelectInput, {
    type EnhancedSelectInputProps,
    type EnhancedSelectInputValue,
} from '../EnhancedSelectInput';
import type { MonitoringScheme } from 'Volume/Volume';

// Types
export interface MonitorIssuesSelectInputProps<K extends string> extends Omit<
    EnhancedSelectInputProps<
        K,
        EnhancedSelectInputValue<MonitoringScheme>,
        MonitoringScheme
    >,
    'values'
> {
    includeNoChange?: boolean;
}

// IMPLEMENTATIONS

export default function MonitorIssuesSelectInput<K extends string>({
    includeNoChange = false,
    ...otherProps
}: MonitorIssuesSelectInputProps<K>) {
    const values: EnhancedSelectInputValue<MonitoringScheme>[] = [
        ...monitorOptions,
    ];

    if (includeNoChange) {
        values.unshift({
            key: 'noChange',
            get value() {
                return translate('NoChange');
            },
            isDisabled: true,
        });
    }

    return <EnhancedSelectInput {...otherProps} values={values} />;
}
