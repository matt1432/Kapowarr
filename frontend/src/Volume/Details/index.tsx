// IMPORTS

// React
import { useCallback, useMemo, useState } from 'react';

// Redux
import { useRootSelector } from 'Store/createAppStore';
import { getVolumeStatus } from 'Store/Slices/SocketEvents';

import { useExecuteCommandMutation } from 'Store/Api/Command';
import {
    useGetVolumesQuery,
    useSearchVolumeQuery,
    useUpdateVolumeMutation,
} from 'Store/Api/Volumes';

// Misc
import {
    commandNames,
    icons,
    kinds,
    massEditActions,
    scrollDirections,
    sizes,
    socketEvents,
    tooltipPositions,
} from 'Helpers/Props';

import sortByProp from 'Utilities/Array/sortByProp';
import translate from 'Utilities/String/translate';
import formatBytes from 'Utilities/Number/formatBytes';

// Hooks
import useSocketCallback from 'Helpers/Hooks/useSocketCallback';

// General Components
import Alert from 'Components/Alert';
import Icon from 'Components/Icon';
import InnerHTML from 'Components/InnerHTML';
import Label from 'Components/Label';
import IconButton from 'Components/Link/IconButton';
import LoadingIndicator from 'Components/Loading/LoadingIndicator';
import MetadataAttribution from 'Components/MetadataAttribution';
import MonitorToggleButton from 'Components/MonitorToggleButton';
import PageContent from 'Components/Page/PageContent';
import PageContentBody from 'Components/Page/PageContentBody';
import PageToolbar from 'Components/Page/Toolbar/PageToolbar';
import PageToolbarButton from 'Components/Page/Toolbar/PageToolbarButton';
import PageToolbarSection from 'Components/Page/Toolbar/PageToolbarSection';
import PageToolbarSeparator from 'Components/Page/Toolbar/PageToolbarSeparator';
import Scroller from 'Components/Scroller/Scroller';
import Tooltip from 'Components/Tooltip/Tooltip';

// Specific Components
import DeleteVolumeModal from 'Volume/Delete/DeleteVolumeModal';
import EditVolumeModal from 'Volume/Edit/EditVolumeModal';
import OrganizePreviewModal from 'Organize/OrganizePreviewModal';
import ConvertPreviewModal from 'Convert/ConvertPreviewModal';
import GeneralFilesModal from 'Volume/GeneralFiles/GeneralFilesModal';
import MonitoringOptionsModal from 'Volume/MonitoringOptions/MonitoringOptionsModal';
import SearchVolumeModal from 'Volume/Search/SearchVolumeModal';
import VolumeHistoryModal from 'Volume/History/VolumeHistoryModal';

import IssueTable from './IssueTable';
import Links from './Links';
import ProgressLabel from './ProgressLabel';
import VolumePoster from 'Volume/VolumePoster';

// CSS
import styles from './index.module.css';

// Types
import type { SocketEventHandler } from 'typings/Socket';

interface VolumeDetailsProps {
    volumeId: number;
}

// IMPLEMENTATIONS

export default function VolumeDetails({ volumeId }: VolumeDetailsProps) {
    const calledFrom = useMemo(() => `VolumeDetails${volumeId}`, [volumeId]);

    const { isRefreshing, isSearching } = useRootSelector((state) =>
        getVolumeStatus(state, volumeId),
    );

    const { allVolumes, volumePublicInfo } = useGetVolumesQuery(undefined, {
        selectFromResult: ({ data }) => ({
            allVolumes: data ?? [],
            volumePublicInfo: data?.find((item) => item.id === volumeId),
        }),
    });

    const {
        volume,
        isFetching,
        isPopulated,
        error,
        hasIssues,
        issueFileCount,
        hasMonitoredIssues,
        refetch,
    } = useSearchVolumeQuery(
        { volumeId },
        {
            refetchOnMountOrArgChange: true,
            selectFromResult: ({
                data,
                error,
                isFetching,
                isUninitialized,
            }) => ({
                volume: data,
                hasIssues: Boolean(data?.issues.length),
                issueFileCount:
                    data?.issues.reduce(
                        (acc, v) => (acc += v.files.length),
                        0,
                    ) ?? 0,
                hasMonitoredIssues: data?.issues.some((e) => e.monitored),
                error,
                isFetching,
                isPopulated: !isUninitialized,
            }),
        },
    );

    const [executeCommand] = useExecuteCommandMutation();
    const [toggleVolumeMonitored] = useUpdateVolumeMutation();

    const [isToggling, setIsToggling] = useState(false);

    const socketCallback = useCallback<
        SocketEventHandler<typeof socketEvents.VOLUME_UPDATED>
    >(
        (data) => {
            if (data.calledFrom === calledFrom) {
                setIsToggling(false);
            }
        },
        [calledFrom],
    );
    useSocketCallback(socketEvents.VOLUME_UPDATED, socketCallback);

    const updateAllSocketCallback = useCallback<
        SocketEventHandler<typeof socketEvents.MASS_EDITOR_STATUS>
    >(
        (data) => {
            if (data.identifier === massEditActions.UPDATE) {
                refetch();
            }
        },
        [refetch],
    );
    useSocketCallback(socketEvents.MASS_EDITOR_STATUS, updateAllSocketCallback);

    const { nextVolume, previousVolume } = useMemo(() => {
        const sortedVolume = allVolumes.toSorted(sortByProp('title'));
        const volumeIndex = sortedVolume.findIndex(
            (volume) => volume.id === volumeId,
        );

        if (volumeIndex === -1) {
            return {
                nextVolume: undefined,
                previousVolume: undefined,
            };
        }

        const nextVolume = sortedVolume[volumeIndex + 1] ?? sortedVolume[0];
        const previousVolume =
            sortedVolume[volumeIndex - 1] ?? sortedVolume.at(-1)!;

        return {
            nextVolume: {
                title: nextVolume.title,
                titleSlug: nextVolume.id,
            },
            previousVolume: {
                title: previousVolume.title,
                titleSlug: previousVolume.id,
            },
        };
    }, [volumeId, allVolumes]);

    const [isOrganizeModalOpen, setIsOrganizeModalOpen] = useState(false);
    const [isConvertModalOpen, setIsConvertModalOpen] = useState(false);
    const [isVolumeHistoryModalOpen, setIsVolumeHistoryModalOpen] =
        useState(false);
    const [isGeneralFilesModalOpen, setIsGeneralFilesModalOpen] =
        useState(false);
    const [isEditVolumeModalOpen, setIsEditVolumeModalOpen] = useState(false);
    const [isDeleteVolumeModalOpen, setIsDeleteVolumeModalOpen] =
        useState(false);
    const [isMonitorOptionsModalOpen, setIsMonitorOptionsModalOpen] =
        useState(false);
    const [isSearchVolumeModalOpen, setIsSearchVolumeModalOpen] =
        useState(false);

    const handleOrganizePress = useCallback(() => {
        setIsOrganizeModalOpen(true);
    }, []);

    const handleOrganizeModalClose = useCallback(() => {
        setIsOrganizeModalOpen(false);
    }, []);

    const handleConvertPress = useCallback(() => {
        setIsConvertModalOpen(true);
    }, []);

    const handleConvertModalClose = useCallback(() => {
        setIsConvertModalOpen(false);
    }, []);

    const handleVolumeHistoryPress = useCallback(() => {
        setIsVolumeHistoryModalOpen(true);
    }, []);

    const handleVolumeHistoryModalClose = useCallback(() => {
        setIsVolumeHistoryModalOpen(false);
    }, []);

    const handleGeneralFilesPress = useCallback(() => {
        setIsGeneralFilesModalOpen(true);
    }, []);

    const handleGeneralFilesModalClose = useCallback(() => {
        setIsGeneralFilesModalOpen(false);
    }, []);

    const handleEditVolumePress = useCallback(() => {
        setIsEditVolumeModalOpen(true);
    }, []);

    const handleEditVolumeModalClose = useCallback(() => {
        setIsEditVolumeModalOpen(false);
    }, []);

    const handleSearchVolumePress = useCallback(() => {
        setIsSearchVolumeModalOpen(true);
    }, []);

    const handleSearchVolumeModalClose = useCallback(() => {
        setIsSearchVolumeModalOpen(false);
    }, []);

    const handleDeleteVolumePress = useCallback(() => {
        setIsEditVolumeModalOpen(false);
        setIsDeleteVolumeModalOpen(true);
    }, []);

    const handleDeleteVolumeModalClose = useCallback(() => {
        setIsDeleteVolumeModalOpen(false);
    }, []);

    const handleMonitorOptionsPress = useCallback(() => {
        setIsMonitorOptionsModalOpen(true);
    }, []);

    const handleMonitorOptionsClose = useCallback(() => {
        setIsMonitorOptionsModalOpen(false);
    }, []);

    const handleMonitorTogglePress = useCallback(
        (value: boolean) => {
            setIsToggling(true);
            toggleVolumeMonitored({
                volumeId,
                monitored: value,
                calledFrom,
            });
        },
        [calledFrom, volumeId, toggleVolumeMonitored],
    );

    const handleRefreshPress = useCallback(() => {
        executeCommand({
            cmd: commandNames.REFRESH_VOLUME,
            volumeId,
        });
    }, [volumeId, executeCommand]);

    const handleSearchPress = useCallback(() => {
        executeCommand({
            cmd: commandNames.VOLUME_SEARCH,
            volumeId,
        });
    }, [volumeId, executeCommand]);

    if (!volume) {
        return null;
    }

    const {
        title,
        folder,
        monitored,
        publisher,
        siteUrl,
        marvelId,
        description,
        totalSize,
    } = volume;

    let issueFilesCountMessage = translate('VolumeDetailsNoIssueFiles');

    if (issueFileCount === 1) {
        issueFilesCountMessage = translate('VolumeDetailsOneIssueFile');
    }
    else if (issueFileCount > 1) {
        issueFilesCountMessage = translate('VolumeDetailsCountIssueFiles', {
            issueFileCount,
        });
    }

    return (
        <PageContent title={title}>
            <PageToolbar>
                <PageToolbarSection>
                    <PageToolbarButton
                        label={translate('RefreshAndScan')}
                        iconName={icons.REFRESH}
                        spinningName={icons.REFRESH}
                        title={translate('RefreshAndScanTooltip')}
                        isSpinning={isRefreshing}
                        onPress={handleRefreshPress}
                    />

                    <PageToolbarButton
                        label={translate('SearchMonitored')}
                        iconName={icons.SEARCH}
                        isDisabled={
                            !monitored || !hasMonitoredIssues || !hasIssues
                        }
                        isSpinning={isSearching}
                        title={
                            hasMonitoredIssues
                                ? undefined
                                : translate('NoMonitoredIssues')
                        }
                        onPress={handleSearchPress}
                    />

                    <PageToolbarButton
                        label={translate('InteractiveSearch')}
                        iconName={icons.INTERACTIVE}
                        isDisabled={
                            !monitored || !hasMonitoredIssues || !hasIssues
                        }
                        isSpinning={false}
                        title={
                            hasMonitoredIssues
                                ? undefined
                                : translate('NoMonitoredIssues')
                        }
                        onPress={handleSearchVolumePress}
                    />

                    <PageToolbarSeparator />

                    <PageToolbarButton
                        label={translate('PreviewRename')}
                        iconName={icons.ORGANIZE}
                        isDisabled={issueFileCount === 0}
                        onPress={handleOrganizePress}
                    />

                    <PageToolbarButton
                        label={translate('PreviewConvert')}
                        iconName={icons.CONVERT}
                        isDisabled={issueFileCount === 0}
                        onPress={handleConvertPress}
                    />

                    <PageToolbarButton
                        label={translate('History')}
                        iconName={icons.HISTORY}
                        isDisabled={!hasIssues}
                        onPress={handleVolumeHistoryPress}
                    />

                    <PageToolbarSeparator />

                    <PageToolbarButton
                        label={translate('GeneralFiles')}
                        iconName={icons.GENERAL_FILES}
                        isDisabled={issueFileCount === 0}
                        onPress={handleGeneralFilesPress}
                    />

                    <PageToolbarButton
                        label={translate('IssueMonitoring')}
                        iconName={icons.MONITORED}
                        onPress={handleMonitorOptionsPress}
                    />

                    <PageToolbarButton
                        label={translate('Edit')}
                        iconName={icons.EDIT}
                        onPress={handleEditVolumePress}
                    />

                    <PageToolbarButton
                        label={translate('Delete')}
                        iconName={icons.DELETE}
                        onPress={handleDeleteVolumePress}
                    />
                </PageToolbarSection>
            </PageToolbar>

            <PageContentBody innerClassName={styles.innerContentBody}>
                <div className={styles.header}>
                    <div className={styles.backdrop}>
                        <div className={styles.backdropOverlay} />
                    </div>

                    <div className={styles.headerContent}>
                        <VolumePoster
                            volume={volume}
                            className={styles.poster}
                            size={500}
                            lazy={false}
                        />

                        <div className={styles.info}>
                            <div className={styles.titleRow}>
                                <div className={styles.titleContainer}>
                                    <div
                                        className={
                                            styles.toggleMonitoredContainer
                                        }
                                    >
                                        <MonitorToggleButton
                                            className={
                                                styles.monitorToggleButton
                                            }
                                            monitored={monitored}
                                            isSaving={isToggling}
                                            size={40}
                                            onPress={handleMonitorTogglePress}
                                        />
                                    </div>

                                    <div className={styles.title}>{title}</div>
                                </div>

                                <div className={styles.volumeNavigationButtons}>
                                    {previousVolume ? (
                                        <IconButton
                                            className={
                                                styles.volumeNavigationButton
                                            }
                                            name={icons.ARROW_LEFT}
                                            size={30}
                                            title={translate(
                                                'VolumeDetailsGoTo',
                                                {
                                                    title: previousVolume.title,
                                                },
                                            )}
                                            to={`/volumes/${previousVolume.titleSlug}`}
                                        />
                                    ) : null}

                                    {nextVolume ? (
                                        <IconButton
                                            className={
                                                styles.volumeNavigationButton
                                            }
                                            name={icons.ARROW_RIGHT}
                                            size={30}
                                            title={translate(
                                                'VolumeDetailsGoTo',
                                                {
                                                    title: nextVolume.title,
                                                },
                                            )}
                                            to={`/volumes/${nextVolume.titleSlug}`}
                                        />
                                    ) : null}
                                </div>
                            </div>

                            <div>
                                <Label
                                    className={styles.detailsLabel}
                                    size={sizes.LARGE}
                                >
                                    <div>
                                        <Icon name={icons.FOLDER} size={17} />
                                        <span className={styles.path}>
                                            {folder}
                                        </span>
                                    </div>
                                </Label>

                                <Tooltip
                                    anchor={
                                        <Label
                                            className={styles.detailsLabel}
                                            size={sizes.LARGE}
                                        >
                                            <div>
                                                <Icon
                                                    name={icons.DRIVE}
                                                    size={17}
                                                />

                                                <span
                                                    className={
                                                        styles.sizeOnDisk
                                                    }
                                                >
                                                    {formatBytes(totalSize)}
                                                </span>
                                            </div>
                                        </Label>
                                    }
                                    tooltip={
                                        <span>{issueFilesCountMessage}</span>
                                    }
                                    kind={kinds.INVERSE}
                                    position={tooltipPositions.BOTTOM}
                                />

                                <Label
                                    className={styles.detailsLabel}
                                    size={sizes.LARGE}
                                >
                                    <div>
                                        <Icon
                                            name={
                                                monitored
                                                    ? icons.MONITORED
                                                    : icons.UNMONITORED
                                            }
                                            size={17}
                                        />
                                        <span
                                            className={
                                                styles.qualityProfileName
                                            }
                                        >
                                            {monitored
                                                ? translate('Monitored')
                                                : translate('Unmonitored')}
                                        </span>
                                    </div>
                                </Label>

                                {publisher ? (
                                    <Label
                                        className={styles.detailsLabel}
                                        title={translate('Publisher')}
                                        size={sizes.LARGE}
                                    >
                                        <div>
                                            <Icon
                                                name={icons.PUBLISHER}
                                                size={17}
                                            />
                                            <span className={styles.network}>
                                                {publisher}
                                            </span>
                                        </div>
                                    </Label>
                                ) : null}

                                <Tooltip
                                    anchor={
                                        <Label
                                            className={styles.detailsLabel}
                                            size={sizes.LARGE}
                                        >
                                            <div>
                                                <Icon
                                                    name={icons.EXTERNAL_LINK}
                                                    size={17}
                                                />
                                                <span className={styles.links}>
                                                    {translate('Links')}
                                                </span>
                                            </div>
                                        </Label>
                                    }
                                    tooltip={
                                        <Links
                                            siteUrl={siteUrl}
                                            marvelId={marvelId}
                                        />
                                    }
                                    kind={kinds.INVERSE}
                                    position={tooltipPositions.BOTTOM}
                                />

                                {volumePublicInfo ? (
                                    <ProgressLabel
                                        className={styles.volumeProgressLabel}
                                        volume={volumePublicInfo}
                                    />
                                ) : null}
                            </div>

                            <Scroller
                                className={styles.overview}
                                scrollDirection={scrollDirections.VERTICAL}
                                autoFocus={false}
                            >
                                <InnerHTML innerHTML={description} />
                            </Scroller>

                            <MetadataAttribution />
                        </div>
                    </div>
                </div>

                <div className={styles.contentContainer}>
                    {!isPopulated && !error ? <LoadingIndicator /> : null}

                    {!isFetching && error ? (
                        <Alert kind={kinds.DANGER}>
                            {translate('IssuesLoadError')}
                        </Alert>
                    ) : null}

                    <IssueTable volumeId={volumeId} />
                </div>

                <OrganizePreviewModal
                    isOpen={isOrganizeModalOpen}
                    volumeId={volumeId}
                    onModalClose={handleOrganizeModalClose}
                />

                <ConvertPreviewModal
                    isOpen={isConvertModalOpen}
                    volumeId={volumeId}
                    onModalClose={handleConvertModalClose}
                />

                <VolumeHistoryModal
                    isOpen={isVolumeHistoryModalOpen}
                    volumeId={volumeId}
                    onModalClose={handleVolumeHistoryModalClose}
                />

                <GeneralFilesModal
                    isOpen={isGeneralFilesModalOpen}
                    volumeId={volumeId}
                    onModalClose={handleGeneralFilesModalClose}
                />

                <EditVolumeModal
                    isOpen={isEditVolumeModalOpen}
                    volumeId={volumeId}
                    onModalClose={handleEditVolumeModalClose}
                    onDeleteVolumePress={handleDeleteVolumePress}
                />

                <DeleteVolumeModal
                    isOpen={isDeleteVolumeModalOpen}
                    volumeId={volumeId}
                    onModalClose={handleDeleteVolumeModalClose}
                />

                <MonitoringOptionsModal
                    isOpen={isMonitorOptionsModalOpen}
                    volumeId={volumeId}
                    onModalClose={handleMonitorOptionsClose}
                />

                <SearchVolumeModal
                    isOpen={isSearchVolumeModalOpen}
                    volumeId={volumeId}
                    onModalClose={handleSearchVolumeModalClose}
                />
            </PageContentBody>
        </PageContent>
    );
}
