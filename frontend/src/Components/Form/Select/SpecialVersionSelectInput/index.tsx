// IMPORTS

// React
import { useMemo } from 'react';

// Misc
import translate from 'Utilities/String/translate';

import { specialVersions } from 'Helpers/Props';

// Specific Components
import EnhancedSelectInput, {
    type EnhancedSelectInputProps,
    type EnhancedSelectInputValue,
} from '../EnhancedSelectInput';
import SpecialVersionSelectInputOption from '../SpecialVersionSelectInputOption';
import SpecialVersionSelectInputSelectedValue from '../SpecialVersionSelectInputSelectedValue';

// Types
import type { SpecialVersion } from 'Helpers/Props/specialVersions';

export interface SpecialVersionSelectInputProps<K extends string> extends Omit<
    EnhancedSelectInputProps<
        K,
        EnhancedSelectInputValue<SpecialVersion>,
        SpecialVersion
    >,
    'values'
> {
    includeNoChange?: boolean;
    includeNoChangeDisabled?: boolean;
    includeMixed?: boolean;
}

export interface ISpecialVersionOption {
    key: SpecialVersion;
    value: string;
    isDisabled?: boolean;
}

// IMPLEMENTATIONS

const specialVersionOptions: ISpecialVersionOption[] = [
    {
        key: specialVersions.NORMAL,
        value: 'Normal',
    },
    {
        key: specialVersions.TPB,
        value: 'Trade Paperback',
    },
    {
        key: specialVersions.ONE_SHOT,
        value: 'Oneshot',
    },
    {
        key: specialVersions.HARD_COVER,
        value: 'Hard Cover',
    },
    {
        key: specialVersions.OMNIBUS,
        value: 'Omnibus',
    },
    {
        key: specialVersions.VOL_AS_ISSUE,
        value: 'Volume as Issue',
    },
];

export default function SpecialVersionSelectInput<K extends string>(
    props: SpecialVersionSelectInputProps<K>,
) {
    const {
        includeNoChange = false,
        includeNoChangeDisabled = true,
        includeMixed = false,
    } = props;

    const values = useMemo(() => {
        const result = [...specialVersionOptions];

        if (includeNoChange) {
            result.unshift({
                key: 'noChange' as SpecialVersion,
                value: translate('NoChange'),
                isDisabled: includeNoChangeDisabled,
            });
        }

        if (includeMixed) {
            result.unshift({
                key: 'mixed' as SpecialVersion,
                value: `(${translate('Mixed')})`,
                isDisabled: true,
            });
        }

        return result;
    }, [includeNoChange, includeNoChangeDisabled, includeMixed]);

    return (
        <EnhancedSelectInput
            {...props}
            values={values}
            optionComponent={SpecialVersionSelectInputOption}
            selectedValueComponent={SpecialVersionSelectInputSelectedValue}
        />
    );
}
