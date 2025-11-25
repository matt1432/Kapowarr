// IMPORTS

// React
import { useCallback, useState } from 'react';

// Redux
import {
    useGetFileQuery,
    useUpdateFileMutation,
    type UpdateFileParams,
} from 'Store/Api/Files';

// Misc
import { inputTypes, kinds, sizes } from 'Helpers/Props';

import translate from 'Utilities/String/translate';

// General Components
import Form from 'Components/Form/Form';
import FormGroup from 'Components/Form/FormGroup';
import FormInputGroup from 'Components/Form/FormInputGroup';
import FormLabel from 'Components/Form/FormLabel';
import Button from 'Components/Link/Button';
import SpinnerErrorButton from 'Components/Link/SpinnerErrorButton';
import ModalBody from 'Components/Modal/ModalBody';
import ModalContent from 'Components/Modal/ModalContent';
import ModalFooter from 'Components/Modal/ModalFooter';
import ModalHeader from 'Components/Modal/ModalHeader';

// CSS
import styles from './index.module.css';

// Types
import type { InputChanged } from 'typings/Inputs';
import type {
    QueryActionCreatorResult,
    QueryDefinition,
} from '@reduxjs/toolkit/query';
import type { CustomBaseQuery } from 'Store/Api/base';
import type { Volume } from 'Volume/Volume';

export interface EditFileModalContentProps {
    fileId: number;
    onModalClose: () => void;
    onDeleteFilePress: () => void;
    refetchFiles: () => QueryActionCreatorResult<
        QueryDefinition<
            { volumeId: number },
            CustomBaseQuery,
            never,
            Volume,
            'api',
            unknown
        >
    >;
}

// IMPLEMENTATIONS

export default function EditFileModalContent({
    fileId,
    onModalClose,
    onDeleteFilePress,
    refetchFiles,
}: EditFileModalContentProps) {
    const [updateFile, { isLoading: isSaving, error: saveError }] =
        useUpdateFileMutation();

    const { data, title } = useGetFileQuery(
        { fileId },
        {
            refetchOnMountOrArgChange: true,
            selectFromResult: ({ data }) => ({
                data,
                title: data?.filepath?.split('/').at(-1) ?? '',
            }),
        },
    );

    const [dpi, setDpi] = useState(data?.dpi ?? '');
    const [releaser, setReleaser] = useState(data?.releaser ?? '');
    const [resolution, setResolution] = useState(data?.resolution ?? '');
    const [scanType, setScanType] = useState(data?.scanType ?? '');
    const [notes, setNotes] = useState(data?.notes ?? '');

    const [prevData, setPrevData] = useState(data);
    if (data !== prevData) {
        setPrevData(data);

        if (data) {
            setDpi(data.dpi ?? '');
            setReleaser(data.releaser ?? '');
            setResolution(data.resolution ?? '');
            setScanType(data.scanType ?? '');
            setNotes(data.notes ?? '');
        }
    }

    const handleInputChange = useCallback(
        <K extends keyof UpdateFileParams>({
            name,
            value,
        }: InputChanged<K, string>) => {
            switch (name) {
                case 'dpi':
                    setDpi(value);
                    break;
                case 'releaser':
                    setReleaser(value);
                    break;
                case 'resolution':
                    setResolution(value);
                    break;
                case 'scanType':
                    setScanType(value);
                    break;
                case 'notes':
                    setNotes(value);
                    break;
            }
        },
        [],
    );

    const handleSavePress = useCallback(async () => {
        const { error: updateError } = await updateFile({
            fileId,
            dpi,
            releaser,
            resolution,
            scanType,
            notes,
        });

        if (!updateError) {
            await refetchFiles();

            onModalClose();
        }
    }, [
        dpi,
        releaser,
        resolution,
        scanType,
        notes,
        updateFile,
        fileId,
        refetchFiles,
        onModalClose,
    ]);

    return (
        <ModalContent onModalClose={onModalClose}>
            <ModalHeader>
                {translate('EditFileModalHeader', { title })}
            </ModalHeader>

            <ModalBody>
                <Form>
                    <FormGroup size={sizes.MEDIUM}>
                        <FormLabel>{translate('DPI')}</FormLabel>

                        <FormInputGroup
                            type={inputTypes.TEXT}
                            name="dpi"
                            value={dpi}
                            helpText={translate('DPIHelpText')}
                            onChange={handleInputChange}
                        />
                    </FormGroup>

                    <FormGroup size={sizes.MEDIUM}>
                        <FormLabel>{translate('ReleaseGroup')}</FormLabel>

                        <FormInputGroup
                            type={inputTypes.TEXT}
                            name="releaser"
                            value={releaser}
                            helpText={translate('ReleaseGroupHelpText')}
                            onChange={handleInputChange}
                        />
                    </FormGroup>

                    <FormGroup size={sizes.MEDIUM}>
                        <FormLabel>{translate('Resolution')}</FormLabel>

                        <FormInputGroup
                            type={inputTypes.TEXT}
                            name="resolution"
                            value={resolution}
                            helpText={translate('ResolutionHelpText')}
                            onChange={handleInputChange}
                        />
                    </FormGroup>

                    <FormGroup size={sizes.MEDIUM}>
                        <FormLabel>{translate('ScanType')}</FormLabel>

                        <FormInputGroup
                            type={inputTypes.TEXT}
                            name="scanType"
                            value={scanType}
                            helpText={translate('ScanTypeHelpText')}
                            onChange={handleInputChange}
                        />
                    </FormGroup>

                    <FormGroup size={sizes.MEDIUM}>
                        <FormLabel>{translate('Notes')}</FormLabel>

                        <FormInputGroup
                            type={inputTypes.TEXT}
                            name="notes"
                            value={notes}
                            helpText={translate('NotesHelpText')}
                            onChange={handleInputChange}
                        />
                    </FormGroup>
                </Form>
            </ModalBody>

            <ModalFooter>
                <Button
                    className={styles.deleteButton}
                    kind={kinds.DANGER}
                    onPress={onDeleteFilePress}
                >
                    {translate('Delete')}
                </Button>

                <Button onPress={onModalClose}>{translate('Cancel')}</Button>

                <SpinnerErrorButton
                    error={saveError}
                    isSpinning={isSaving}
                    onPress={handleSavePress}
                >
                    {translate('Save')}
                </SpinnerErrorButton>
            </ModalFooter>
        </ModalContent>
    );
}
