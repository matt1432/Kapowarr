// IMPORTS

// React
import { useCallback, useMemo, useRef, useState, type RefObject } from 'react';

import {
    useListRef,
    type ListImperativeAPI,
    type RowComponentProps,
} from 'react-window';

// Redux
import { useRootSelector } from 'Store/createAppStore';

import { useGetFileQuery } from 'Store/Api/Files';
import { useUpdateBookPagesMutation } from 'Store/Api/Issues';

// Misc
import { icons } from 'Helpers/Props';

import translate from 'Utilities/String/translate';

// General Components
import Button from 'Components/Link/Button';
import IconButton from 'Components/Link/IconButton';
import LoadingIndicator from 'Components/Loading/LoadingIndicator';
import ModalBody from 'Components/Modal/ModalBody';
import ModalContent from 'Components/Modal/ModalContent';
import ModalFooter from 'Components/Modal/ModalFooter';
import ModalHeader from 'Components/Modal/ModalHeader';
import SpinnerErrorButton from 'Components/Link/SpinnerErrorButton';
import SpinnerIconButton from 'Components/Link/SpinnerIconButton';
import TextInput from 'Components/Form/TextInput';
import VirtualTable from 'Components/Table/VirtualTable';

// CSS
import styles from './index.module.css';

// Types
import type { ThumbnailData } from 'Store/Api/Issues';
import type { InputChanged } from 'typings/Inputs';

interface RowProps {
    thumbnails: ThumbnailData[];
    handlePressUp: (index: number) => () => void;
    handlePressDown: (index: number) => () => void;
    handlePressDelete: (index: number) => () => void;
    handleEditFilename: (
        index: number,
    ) => (change: InputChanged<'filename', string>) => void;
}

export interface EditPagesModalContentProps {
    fileId: number;
    thumbnails: ThumbnailData[] | undefined;
    isRefreshing: boolean;
    onRefresh: () => void;
    onModalClose: () => void;
}

// IMPLEMENTATIONS

function parsePageNumbers(
    filename: string,
    prefix: string,
): string | [string, string, string] {
    const strippedName = filename
        .replace(prefix, '')
        .replace(/\.[^.]*$/, '')
        .trim();

    const separator = strippedName.replace(/\d/g, '');

    if (separator === '') {
        return strippedName;
    }

    const parsedNumbers = strippedName.split(separator);

    return [parsedNumbers[0], parsedNumbers[1], separator];
}

function swapThumbnailPositions([first, secnd]: [
    ThumbnailData,
    ThumbnailData,
]): [ThumbnailData, ThumbnailData] {
    const prefix = first.prefix;

    let newFirstFilename = secnd.newFilename;
    let newSecndFilename = first.newFilename;

    const firstNumbers = parsePageNumbers(first.newFilename, prefix);
    const secndNumbers = parsePageNumbers(secnd.newFilename, prefix);

    if (typeof firstNumbers === 'string' && typeof secndNumbers !== 'string') {
        const separator = secndNumbers[2];
        newFirstFilename = first.newFilename.replace(
            firstNumbers,
            secndNumbers[1],
        );
        newSecndFilename = secnd.newFilename.replace(
            `${secndNumbers[0]}${separator}${secndNumbers[1]}`,
            `${firstNumbers}${separator}${secndNumbers[0]}`,
        );
    }
    else if (
        typeof firstNumbers !== 'string' &&
        typeof secndNumbers === 'string'
    ) {
        const separator = firstNumbers[2];
        newFirstFilename = first.newFilename.replace(
            `${firstNumbers[0]}${separator}${firstNumbers[1]}`,
            `${firstNumbers[1]}${separator}${secndNumbers}`,
        );
        newSecndFilename = secnd.newFilename.replace(
            secndNumbers,
            firstNumbers[0],
        );
    }

    return [
        {
            ...secnd,
            newFilename: newSecndFilename,
        },
        {
            ...first,
            newFilename: newFirstFilename,
        },
    ];
}

function Row({
    index,
    style,
    thumbnails,
    handlePressUp,
    handlePressDown,
    handlePressDelete,
    handleEditFilename,
}: RowComponentProps<RowProps>) {
    const { src, newFilename } = thumbnails[index];

    const isLast = index === thumbnails.length - 1;

    return (
        <div
            className={styles.row}
            style={{
                borderBottom: isLast ? undefined : 'solid white 1px',
                ...style,
            }}
        >
            <div className={styles.imageContainer}>
                <img
                    // The image at the provided link can change over time
                    // Update it every time we open this window
                    src={`${src}&${new Date().getTime()}`}
                    height={600}
                />

                <div className={styles.buttons}>
                    <IconButton
                        name={icons.ARROW_UP}
                        onPress={handlePressUp(index)}
                        isDisabled={index === 0}
                    />

                    <IconButton
                        name={icons.DELETE}
                        onPress={handlePressDelete(index)}
                    />

                    <IconButton
                        name={icons.ARROW_DOWN}
                        onPress={handlePressDown(index)}
                        isDisabled={isLast}
                    />
                </div>
            </div>

            <div className={styles.inputContainer}>
                <TextInput
                    name="filename"
                    value={newFilename}
                    onChange={handleEditFilename(index)}
                />
            </div>
        </div>
    );
}

export default function EditPagesModalContent({
    fileId,
    thumbnails,
    onRefresh,
    isRefreshing,
    onModalClose,
}: EditPagesModalContentProps) {
    const { title } = useGetFileQuery(
        { fileId },
        {
            refetchOnMountOrArgChange: true,
            selectFromResult: ({ data }) => ({
                title: data?.filepath?.split('/').at(-1) ?? '',
            }),
        },
    );

    // Table
    const { isSmallScreen } = useRootSelector((state) => state.app.dimensions);

    const scrollerRef = useRef<HTMLDivElement>(
        null,
    ) as RefObject<HTMLDivElement>;

    const listRef = useListRef(undefined) as RefObject<ListImperativeAPI>;

    // Edits
    const [changes, setChanges] = useState(thumbnails);

    const [prevThumbnails, setPrevThumbnails] = useState(thumbnails);
    if (thumbnails !== prevThumbnails) {
        setPrevThumbnails(thumbnails);
        setChanges(
            thumbnails?.toSorted((a, b) =>
                a.newFilename.localeCompare(b.newFilename),
            ),
        );
    }

    const [updateBookPages, { isLoading: isSaving, error: saveError }] =
        useUpdateBookPagesMutation();

    const canSave = useMemo(
        () =>
            changes &&
            JSON.stringify(
                thumbnails?.toSorted((a, b) =>
                    a.newFilename.localeCompare(b.newFilename),
                ),
            ) !== JSON.stringify(changes),
        [changes, thumbnails],
    );

    const handleSavePress = useCallback(() => {
        if (!changes) {
            return;
        }
        updateBookPages({
            fileId,
            newPages: changes,
        });
    }, [changes, fileId, updateBookPages]);

    const handlePressUp = useCallback(
        (index: number) => () => {
            if (!changes) {
                return;
            }

            const newThumbnails = [...changes];

            const swapped = swapThumbnailPositions([
                changes[index - 1],
                changes[index],
            ]);

            newThumbnails[index - 1] = swapped[0];
            newThumbnails[index] = swapped[1];

            setChanges(newThumbnails);
        },
        [changes],
    );

    const handlePressDown = useCallback(
        (index: number) => () => {
            if (!changes) {
                return;
            }

            const newThumbnails = [...changes];

            const swapped = swapThumbnailPositions([
                changes[index],
                changes[index + 1],
            ]);

            newThumbnails[index] = swapped[0];
            newThumbnails[index + 1] = swapped[1];

            setChanges(newThumbnails);
        },
        [changes],
    );

    const handlePressDelete = useCallback(
        (index: number) => () => {
            if (!changes) {
                return;
            }

            const newThumbnails = [...changes];

            for (let i = index; i !== changes.length - 1; i++) {
                const swapped = swapThumbnailPositions([
                    changes[i],
                    changes[i + 1],
                ]);

                newThumbnails[i] = swapped[0];
                newThumbnails[i + 1] = swapped[1];
            }

            setChanges(newThumbnails.slice(0, -1));
        },
        [changes],
    );

    const handleEditFilename = useCallback(
        (index: number) =>
            ({ value }: InputChanged<'filename', string>) => {
                if (!changes) {
                    return;
                }

                const newThumbnails = [...changes];

                newThumbnails[index] = {
                    ...newThumbnails[index],
                    newFilename: value,
                };

                setChanges(newThumbnails);
            },
        [changes],
    );

    return (
        <ModalContent onModalClose={onModalClose}>
            <ModalHeader className={styles.modalHeaderContainer}>
                <div className={styles.modalHeader}>
                    {translate('EditPagesModalHeader', { title })}
                </div>

                <SpinnerIconButton
                    name={icons.REFRESH}
                    className={styles.refreshButton}
                    size={18}
                    onPress={onRefresh}
                    isSpinning={isRefreshing}
                />
            </ModalHeader>

            <ModalBody>
                {changes ? (
                    <VirtualTable
                        Header={<></>}
                        listRef={listRef}
                        itemCount={changes.length}
                        itemData={{
                            thumbnails: changes,
                            handlePressUp,
                            handlePressDown,
                            handlePressDelete,
                            handleEditFilename,
                        }}
                        rowHeight={700}
                        isSmallScreen={isSmallScreen}
                        scrollerRef={scrollerRef}
                        Row={Row}
                    />
                ) : (
                    <LoadingIndicator />
                )}
            </ModalBody>

            <ModalFooter>
                <Button onPress={onModalClose}>{translate('Cancel')}</Button>

                <SpinnerErrorButton
                    error={saveError}
                    isSpinning={isSaving}
                    onPress={handleSavePress}
                    isDisabled={!canSave}
                >
                    {translate('Save')}
                </SpinnerErrorButton>
            </ModalFooter>
        </ModalContent>
    );
}
