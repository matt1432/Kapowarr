// IMPORTS

// Misc
import { inputTypes } from 'Helpers/Props';

import translate from 'Utilities/String/translate';

// Hooks
import useEditSettings from 'Settings/useEditSettings';

// General Components
import FieldSet from 'Components/FieldSet';
import Form from 'Components/Form/Form';
import FormGroup from 'Components/Form/FormGroup';
import FormInputGroup from 'Components/Form/FormInputGroup';
import FormLabel from 'Components/Form/FormLabel';
import PageContent from 'Components/Page/PageContent';
import PageContentBody from 'Components/Page/PageContentBody';
import SettingsToolbar from 'Settings/SettingsToolbar';

// Types
import type { EnhancedSelectInputValue } from 'Components/Form/Select/EnhancedSelectInput';
import type { DateType } from 'Helpers/Props/dateTypes';

// IMPLEMENTATIONS

const dateTypeOptions: EnhancedSelectInputValue<DateType>[] = [
    { key: 'cover_date', value: 'Cover Date' },
    { key: 'store_date', value: 'In Store Date' },
    { key: 'oldest_date', value: 'Oldest Date' },
];

export default function MetadataSettings() {
    const {
        isSaving,
        hasPendingChanges,
        onSavePress,
        handleInputChange,
        changes,
    } = useEditSettings();

    return (
        <PageContent title={translate('MetadataSettings')}>
            <SettingsToolbar
                isSaving={isSaving}
                hasPendingChanges={hasPendingChanges}
                onSavePress={onSavePress}
            />

            <PageContentBody>
                <Form id="metadataSettings">
                    <FieldSet legend={translate('Fetching')}>
                        <FormGroup>
                            <FormLabel>{translate('DateType')}</FormLabel>
                            <FormInputGroup
                                type={inputTypes.SELECT}
                                name="dateType"
                                helpText={translate('DateTypeHelpText')}
                                onChange={handleInputChange}
                                value={changes.dateType}
                                values={dateTypeOptions}
                            />
                        </FormGroup>
                    </FieldSet>
                </Form>
            </PageContentBody>
        </PageContent>
    );
}
