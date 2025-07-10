import { throttle } from 'lodash';
import { type RefObject, useEffect, useMemo, useRef, useState } from 'react';
// import { useSelector } from 'react-redux';
import { FixedSizeGrid as Grid, type GridChildComponentProps } from 'react-window';
// import { createSelector } from 'reselect';
// import { type AppState } from 'App/State/AppState';
import useMeasure from 'Helpers/Hooks/useMeasure';
import { type SortDirection } from 'Helpers/Props/sortDirections';
import VolumesIndexPoster from 'Volumes/Index/Posters/VolumesIndexPoster';
import { type Volumes } from 'Volumes/Volumes';
import dimensions from 'Styles/Variables/dimensions';
import getIndexOfFirstCharacter from 'Utilities/Array/getIndexOfFirstCharacter';

const bodyPadding = parseInt(dimensions.pageContentBodyPadding);
const bodyPaddingSmallScreen = parseInt(dimensions.pageContentBodyPaddingSmallScreen);
const columnPadding = parseInt(dimensions.volumesIndexColumnPadding);
const columnPaddingSmallScreen = parseInt(dimensions.volumesIndexColumnPaddingSmallScreen);
const progressBarHeight = parseInt(dimensions.progressBarSmallHeight);
const detailedProgressBarHeight = parseInt(dimensions.progressBarMediumHeight);

const ADDITIONAL_COLUMN_COUNT: Record<string, number> = {
    small: 3,
    medium: 2,
    large: 1,
};

interface CellItemData {
    layout: {
        columnCount: number;
        padding: number;
        posterWidth: number;
        posterHeight: number;
    };
    items: Volumes[];
    sortKey: string;
    isSelectMode: boolean;
}

interface VolumesIndexPostersProps {
    items: Volumes[];
    sortKey: string;
    sortDirection?: SortDirection;
    jumpToCharacter?: string;
    scrollTop?: number;
    scrollerRef: RefObject<HTMLElement>;
    isSelectMode: boolean;
    isSmallScreen: boolean;
}

/*
const volumesIndexSelector = createSelector(
    (state: AppState) => state.volumesIndex.posterOptions,
    (posterOptions) => {
        return {
            posterOptions,
        };
    },
);
*/

function Cell({ columnIndex, rowIndex, style, data }: GridChildComponentProps<CellItemData>) {
    const { layout, items, sortKey, isSelectMode } = data;
    const { columnCount, padding, posterWidth, posterHeight } = layout;
    const index = rowIndex * columnCount + columnIndex;

    if (index >= items.length) {
        return null;
    }

    const volumes = items[index];

    return (
        <div
            style={{
                padding,
                ...style,
            }}
        >
            <VolumesIndexPoster
                volumesId={volumes.id}
                sortKey={sortKey}
                isSelectMode={isSelectMode}
                posterWidth={posterWidth}
                posterHeight={posterHeight}
            />
        </div>
    );
}

function getWindowScrollTopPosition() {
    return document.documentElement.scrollTop || document.body.scrollTop || 0;
}

export default function VolumesIndexPosters(props: VolumesIndexPostersProps) {
    const { scrollerRef, items, sortKey, jumpToCharacter, isSelectMode, isSmallScreen } = props;

    // const { posterOptions } = useSelector(volumesIndexSelector);
    const ref = useRef<Grid>(null);
    const [measureRef, bounds] = useMeasure();
    const [size, setSize] = useState({ width: 0, height: 0 });

    const columnWidth = useMemo(() => {
        const { width } = size;
        const maximumColumnWidth = isSmallScreen ? 172 : 182;
        const columns = Math.floor(width / maximumColumnWidth);
        const remainder = width % maximumColumnWidth;
        return remainder === 0
            ? maximumColumnWidth
            : Math.floor(width / (columns + ADDITIONAL_COLUMN_COUNT[0 /*posterOptions.size*/]));
    }, [isSmallScreen, /*posterOptions,*/ size]);

    const columnCount = useMemo(
        () => Math.max(Math.floor(size.width / columnWidth), 1),
        [size, columnWidth],
    );
    const padding = props.isSmallScreen ? columnPaddingSmallScreen : columnPadding;
    const posterWidth = columnWidth - padding * 2;
    const posterHeight = Math.ceil((250 / 170) * posterWidth);

    const rowHeight = useMemo(() => {
        // const { detailedProgressBar, showTitle, showMonitored, showQualityProfile, showTags } =
        //    posterOptions;
        const detailedProgressBar = false;
        const showTitle = '';
        const showMonitored = false;
        const showQualityProfile = false;
        const showTags = false;

        const nextAiringHeight = 19;

        const heights = [
            posterHeight,
            detailedProgressBar ? detailedProgressBarHeight : progressBarHeight,
            nextAiringHeight,
            isSmallScreen ? columnPaddingSmallScreen : columnPadding,
        ];

        if (showTitle) {
            heights.push(19);
        }

        if (showMonitored) {
            heights.push(19);
        }

        if (showQualityProfile) {
            heights.push(19);
        }

        if (showTags) {
            heights.push(21);
        }

        switch (sortKey) {
            case 'network':
            case 'seasons':
            case 'previousAiring':
            case 'added':
            case 'path':
            case 'sizeOnDisk':
                heights.push(19);
                break;
            case 'qualityProfileId':
                if (!showQualityProfile) {
                    heights.push(19);
                }
                break;
            case 'tags':
                if (!showTags) {
                    heights.push(21);
                }
                break;
            default:
            // No need to add a height of 0
        }

        return heights.reduce((acc, height) => acc + height, 0);
    }, [isSmallScreen, /* posterOptions, */ sortKey, posterHeight]);

    useEffect(() => {
        const current = scrollerRef.current;

        if (isSmallScreen) {
            const padding = bodyPaddingSmallScreen - 5;
            const width = window.innerWidth - padding * 2;
            const height = window.innerHeight;

            if (width !== size.width || height !== size.height) {
                setSize({
                    width,
                    height,
                });
            }

            return;
        }

        if (current) {
            const width = current.clientWidth;
            const padding = bodyPadding - 5;
            const finalWidth = width - padding * 2;

            if (Math.abs(size.width - finalWidth) < 20 || size.width === finalWidth) {
                return;
            }

            setSize({
                width: finalWidth,
                height: window.innerHeight,
            });
        }
    }, [isSmallScreen, size, scrollerRef, bounds]);

    useEffect(() => {
        const currentScrollerRef = scrollerRef.current as HTMLElement;
        const currentScrollListener = isSmallScreen ? window : currentScrollerRef;

        const handleScroll = throttle(() => {
            const { offsetTop = 0 } = currentScrollerRef;
            const scrollTop =
                (isSmallScreen ? getWindowScrollTopPosition() : currentScrollerRef.scrollTop) -
                offsetTop;

            ref.current?.scrollTo({ scrollLeft: 0, scrollTop });
        }, 10);

        currentScrollListener.addEventListener('scroll', handleScroll);

        return () => {
            handleScroll.cancel();

            if (currentScrollListener) {
                currentScrollListener.removeEventListener('scroll', handleScroll);
            }
        };
    }, [isSmallScreen, ref, scrollerRef]);

    useEffect(() => {
        if (jumpToCharacter) {
            const index = getIndexOfFirstCharacter(items, jumpToCharacter);

            if (index != null) {
                const rowIndex = Math.floor(index / columnCount);

                const scrollTop = rowIndex * rowHeight + padding;

                ref.current?.scrollTo({ scrollLeft: 0, scrollTop });
                scrollerRef.current?.scrollTo(0, scrollTop);
            }
        }
    }, [jumpToCharacter, rowHeight, columnCount, padding, items, scrollerRef, ref]);

    return (
        <div ref={measureRef}>
            <Grid<CellItemData>
                ref={ref}
                style={{
                    width: '100%',
                    height: '100%',
                    overflow: 'none',
                }}
                width={size.width}
                height={size.height}
                columnCount={columnCount}
                columnWidth={columnWidth}
                rowCount={Math.ceil(items.length / columnCount)}
                rowHeight={rowHeight}
                itemData={{
                    layout: {
                        columnCount,
                        padding,
                        posterWidth,
                        posterHeight,
                    },
                    items,
                    sortKey,
                    isSelectMode,
                }}
            >
                {Cell}
            </Grid>
        </div>
    );
}
