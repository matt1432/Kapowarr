// IMPORTS

// React
import { useCallback, useMemo, useRef, useState, type RefObject } from 'react';

// Redux
import { useRootDispatch, useRootSelector } from 'Store/createAppStore';
import {
    setVolumeFilter,
    setVolumeView,
    setVolumeTableOption,
    type VolumeIndexState,
} from 'Store/Slices/VolumeIndex';
import {
    setTableSort,
    type SetTableOptionsParams,
} from 'Store/Slices/TableOptions';
import { setScrollPosition } from 'Store/Slices/App';

import { useGetVolumesQuery } from 'Store/Api/Volumes';

// Misc
import getFilteredVolumeIDs from 'Utilities/Volume/getFilteredVolumeIDs';

import { align, icons, kinds, sortDirections } from 'Helpers/Props';

import translate from 'Utilities/String/translate';

// Hooks
import useSort from 'Helpers/Hooks/useSort';

// General Components
import { SelectProvider } from 'App/SelectContext';

import withScrollPosition from 'Components/withScrollPosition';

import Alert from 'Components/Alert';
import LoadingIndicator from 'Components/Loading/LoadingIndicator';
import NoVolume from 'Volume/NoVolume';
import PageContent from 'Components/Page/PageContent';
import PageContentBody from 'Components/Page/PageContentBody';
import PageJumpBar, {
    type PageJumpBarItems,
} from 'Components/Page/PageJumpBar';
import PageToolbar from 'Components/Page/Toolbar/PageToolbar';
import PageToolbarButton from 'Components/Page/Toolbar/PageToolbarButton';
import PageToolbarSection from 'Components/Page/Toolbar/PageToolbarSection';
import PageToolbarSeparator from 'Components/Page/Toolbar/PageToolbarSeparator';
import TableOptionsModalWrapper from 'Components/Table/TableOptions/TableOptionsModalWrapper';

// Specific Components
import RefreshVolumesButton from './ActionButtons/RefreshVolumesButton';
import SearchVolumesButton from './ActionButtons/SearchVolumesButton';
import VolumeIndexFilterMenu from './Menus/VolumeIndexFilterMenu';
import VolumeIndexSortMenu from './Menus/VolumeIndexSortMenu';
import VolumeIndexViewMenu from './Menus/VolumeIndexViewMenu';
import VolumeIndexPosterOptionsModal from './Posters/Options/VolumeIndexPosterOptionsModal';
import VolumeIndexPosters from './Posters/VolumeIndexPosters';
import VolumeIndexSelectAllButton from './Select/VolumeIndexSelectAllButton';
import VolumeIndexSelectAllMenuItem from './Select/VolumeIndexSelectAllMenuItem';
import VolumeIndexSelectFooter from './Select/VolumeIndexSelectFooter';
import VolumeIndexSelectModeButton from './Select/VolumeIndexSelectModeButton';
import VolumeIndexSelectModeMenuItem from './Select/VolumeIndexSelectModeMenuItem';
import VolumeIndexFooter from './VolumeIndexFooter';
import VolumeIndexTableOptions from './Table/VolumeIndexTableOptions';
import VolumeIndexTable from './Table/VolumeIndexTable';

// CSS
import styles from './index.module.css';

// Types
import type { VolumeIndexColumnName } from './columns';

export type IndexView = 'posters' | 'table';
export type IndexFilter =
    | ''
    | 'monitored'
    | 'unmonitored'
    | 'continuing'
    | 'ended'
    | 'wanted';

interface VolumeIndexProps {
    initialScrollTop?: number;
}

// IMPLEMENTATIONS

const useIndexVolumes = () => {
    const {
        columns,
        sortKey,
        sortDirection,
        secondarySortKey,
        secondarySortDirection,
    } = useRootSelector((state) => state.tableOptions.volumeIndex);

    const { filterKey } = useRootSelector((state) => state.volumeIndex);

    const { isFetching, isPopulated, error, data, totalItems } =
        useGetVolumesQuery(undefined, {
            selectFromResult: ({
                isFetching,
                isUninitialized,
                error,
                data,
            }) => ({
                isFetching,
                isPopulated: !isUninitialized,
                error,
                data: data ?? [],
                totalItems: data?.length ?? 0,
            }),
        });

    const sortedItems = useSort({
        columns,
        items: data,
        sortKey,
        secondarySortKey,
        sortDirection,
        secondarySortDirection,
        predicates: {
            issueCountMonitored: (a, b) =>
                a.issueCountMonitored -
                a.issuesDownloadedMonitored -
                (b.issueCountMonitored - b.issuesDownloadedMonitored),
        },
    });

    const items = useMemo(() => {
        return getFilteredVolumeIDs(sortedItems, filterKey);
    }, [filterKey, sortedItems]);

    return {
        isFetching,
        isPopulated,
        error,
        items,
        totalItems,
    };
};

const VolumeIndex = withScrollPosition(
    ({ initialScrollTop }: VolumeIndexProps) => {
        const dispatch = useRootDispatch();

        const {
            columns,
            sortKey,
            sortDirection,
            secondarySortKey,
            secondarySortDirection,
        } = useRootSelector((state) => state.tableOptions.volumeIndex);

        const { filterKey, view } = useRootSelector(
            (state) => state.volumeIndex,
        );

        const { isFetching, isPopulated, error, items, totalItems } =
            useIndexVolumes();

        const { isSmallScreen } = useRootSelector(
            (state) => state.app.dimensions,
        );
        const scrollerRef = useRef<HTMLDivElement>(
            null,
        ) as RefObject<HTMLDivElement>;
        const [isOptionsModalOpen, setIsOptionsModalOpen] = useState(false);
        const [jumpToCharacter, setJumpToCharacter] = useState<
            string | undefined
        >(undefined);
        const [isSelectMode, setIsSelectMode] = useState(false);

        const onSelectModePress = useCallback(() => {
            setIsSelectMode(!isSelectMode);
        }, [isSelectMode, setIsSelectMode]);

        const onTableOptionChange = useCallback(
            (
                payload: Partial<
                    SetTableOptionsParams<'volumeIndex'> &
                        VolumeIndexState['tableOptions']
                >,
            ) => {
                dispatch(setVolumeTableOption(payload));
            },
            [dispatch],
        );

        const onViewSelect = useCallback(
            (value: IndexView) => {
                dispatch(setVolumeView(value));

                if (scrollerRef.current) {
                    scrollerRef.current.scrollTo(0, 0);
                }
            },
            [scrollerRef, dispatch],
        );

        const onSortSelect = useCallback(
            (sortKey: VolumeIndexColumnName) => {
                dispatch(setTableSort({ tableName: 'volumeIndex', sortKey }));
            },
            [dispatch],
        );

        const onFilterSelect = useCallback(
            (value: IndexFilter) => {
                dispatch(setVolumeFilter(value));
            },
            [dispatch],
        );

        const onOptionsPress = useCallback(() => {
            setIsOptionsModalOpen(true);
        }, [setIsOptionsModalOpen]);

        const onOptionsModalClose = useCallback(() => {
            setIsOptionsModalOpen(false);
        }, [setIsOptionsModalOpen]);

        const onJumpBarItemPress = useCallback(
            (character: string) => {
                setJumpToCharacter(character);
            },
            [setJumpToCharacter],
        );

        const onScroll = useCallback(
            ({ scrollTop }: { scrollTop: number }) => {
                setJumpToCharacter(undefined);
                dispatch(
                    setScrollPosition({
                        name: 'volumeIndex',
                        value: scrollTop,
                    }),
                );
            },
            [dispatch, setJumpToCharacter],
        );

        const jumpBarItems: PageJumpBarItems = useMemo(() => {
            // Reset if not sorting by title
            if (sortKey !== 'title' && secondarySortKey !== 'title') {
                return {
                    characters: {},
                    order: [],
                };
            }

            const characters =
                items.reduce((acc: Record<string, number>, item) => {
                    let char = item.title.charAt(0);

                    if (!isNaN(Number(char))) {
                        char = '#';
                    }

                    if (char in acc) {
                        acc[char] = acc[char] + 1;
                    }
                    else {
                        acc[char] = 1;
                    }

                    return acc;
                }, {}) ?? {};

            const order = Object.keys(characters).sort();

            // Reverse if sorting descending
            if (
                (sortKey === 'title' &&
                    sortDirection === sortDirections.DESCENDING) ||
                (secondarySortKey === 'title' &&
                    secondarySortDirection === sortDirections.DESCENDING)
            ) {
                order.reverse();
            }

            return {
                characters,
                order,
            };
        }, [
            items,
            sortKey,
            sortDirection,
            secondarySortKey,
            secondarySortDirection,
        ]);

        const ViewComponent = useMemo(
            () => (view === 'posters' ? VolumeIndexPosters : VolumeIndexTable),
            [view],
        );

        const isLoaded = !error && isPopulated && totalItems;
        const hasNoVolume = !totalItems;

        return (
            <SelectProvider items={items}>
                <PageContent>
                    <PageToolbar>
                        <PageToolbarSection>
                            <RefreshVolumesButton
                                isSelectMode={isSelectMode}
                                filterKey={filterKey}
                            />

                            <SearchVolumesButton
                                isSelectMode={isSelectMode}
                                filterKey={filterKey}
                            />

                            <PageToolbarSeparator />

                            <VolumeIndexSelectModeButton
                                label={
                                    isSelectMode
                                        ? translate('StopSelecting')
                                        : translate('SelectVolume')
                                }
                                iconName={
                                    isSelectMode
                                        ? icons.VOLUME_ENDED
                                        : icons.CHECK
                                }
                                isSelectMode={isSelectMode}
                                overflowComponent={
                                    VolumeIndexSelectModeMenuItem
                                }
                                onPress={onSelectModePress}
                            />

                            <VolumeIndexSelectAllButton
                                label="SelectAll"
                                isSelectMode={isSelectMode}
                                overflowComponent={VolumeIndexSelectAllMenuItem}
                            />

                            <PageToolbarSeparator />
                        </PageToolbarSection>

                        <PageToolbarSection
                            alignContent={align.RIGHT}
                            collapseButtons={false}
                        >
                            {view === 'table' ? (
                                <TableOptionsModalWrapper
                                    tableName="volumeIndex"
                                    columns={columns}
                                    optionsComponent={VolumeIndexTableOptions}
                                    onTableOptionChange={onTableOptionChange}
                                >
                                    <PageToolbarButton
                                        label={translate('Options')}
                                        iconName={icons.TABLE}
                                    />
                                </TableOptionsModalWrapper>
                            ) : (
                                <PageToolbarButton
                                    label={translate('Options')}
                                    iconName={
                                        view === 'posters'
                                            ? icons.POSTER
                                            : icons.OVERVIEW
                                    }
                                    isDisabled={hasNoVolume}
                                    onPress={onOptionsPress}
                                />
                            )}

                            <PageToolbarSeparator />

                            <VolumeIndexViewMenu
                                view={view}
                                isDisabled={hasNoVolume}
                                onViewSelect={onViewSelect}
                            />

                            <VolumeIndexSortMenu
                                sortKey={sortKey}
                                sortDirection={sortDirection}
                                secondarySortKey={secondarySortKey}
                                secondarySortDirection={secondarySortDirection}
                                isDisabled={hasNoVolume}
                                onSortSelect={onSortSelect}
                            />

                            <VolumeIndexFilterMenu
                                filterKey={filterKey}
                                isDisabled={hasNoVolume}
                                onFilterSelect={onFilterSelect}
                            />
                        </PageToolbarSection>
                    </PageToolbar>

                    <div className={styles.pageContentBodyWrapper}>
                        <PageContentBody
                            ref={scrollerRef}
                            className={styles.contentBody}
                            innerClassName={styles[`${view}InnerContentBody`]}
                            initialScrollTop={initialScrollTop}
                            onScroll={onScroll}
                        >
                            {isFetching && !isPopulated ? (
                                <LoadingIndicator />
                            ) : null}

                            {!isFetching && !!error ? (
                                <Alert kind={kinds.DANGER}>
                                    {translate('VolumeLoadError')}
                                </Alert>
                            ) : null}

                            {isLoaded ? (
                                <div className={styles.contentBodyContainer}>
                                    <ViewComponent
                                        scrollerRef={scrollerRef}
                                        items={items}
                                        jumpToCharacter={jumpToCharacter}
                                        isSelectMode={isSelectMode}
                                        isSmallScreen={isSmallScreen}
                                        columns={columns}
                                    />

                                    <VolumeIndexFooter />
                                </div>
                            ) : null}

                            {!error && isPopulated && !totalItems ? (
                                <NoVolume totalItems={totalItems} />
                            ) : null}
                        </PageContentBody>

                        {isLoaded && !!jumpBarItems.order.length ? (
                            <PageJumpBar
                                items={jumpBarItems}
                                onItemPress={onJumpBarItemPress}
                            />
                        ) : null}
                    </div>

                    {isSelectMode ? <VolumeIndexSelectFooter /> : null}

                    {view === 'posters' ? (
                        <VolumeIndexPosterOptionsModal
                            isOpen={isOptionsModalOpen}
                            onModalClose={onOptionsModalClose}
                        />
                    ) : null}
                </PageContent>
            </SelectProvider>
        );
    },
    'volumeIndex',
);

export default VolumeIndex;
