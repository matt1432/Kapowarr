// IMPORTS

// React
import { useCallback, useMemo } from 'react';

// Redux
import { useRootSelector } from 'Store/createAppStore';

import { useMassEditMutation } from 'Store/Api/Command';
import { useGetVolumesQuery } from 'Store/Api/Volumes';

// Misc
import getFilteredVolumeIDs from 'Utilities/Volume/getFilteredVolumeIDs';
import getSelectedIds from 'Utilities/Table/getSelectedIds';
import translate, { type TranslateKey } from 'Utilities/String/translate';

// Hooks
import { useSelect } from 'App/SelectContext';

// General Components
import PageToolbarButton from 'Components/Page/Toolbar/PageToolbarButton';

// Types
import type { IndexFilter } from '..';
import type { IconName } from 'Components/Icon';

interface ActionButtonProps<T extends 'update' | 'search'> {
    isSelectMode: boolean;
    filterKey: IndexFilter;
    actionKey: T;
    icon: IconName;
    labels: {
        all: TranslateKey;
        filtered: TranslateKey;
        selected: TranslateKey;
    };
}

// IMPLEMENTATIONS

export default function ActionButton<T extends 'update' | 'search'>({
    actionKey,
    filterKey,
    icon,
    isSelectMode,
    labels,
}: ActionButtonProps<T>) {
    const { isRunning } = useRootSelector(
        (state) => state.socketEvents.massEditorStatus[actionKey],
    );

    const { items, totalItems } = useGetVolumesQuery(undefined, {
        selectFromResult: ({ data }) => ({
            items: data ?? [],
            totalItems: data?.length ?? 0,
        }),
    });

    const [{ selectedState }] = useSelect();

    const selectedVolumeIds = useMemo(
        () => getSelectedIds(selectedState),
        [selectedState],
    );

    const volumesToEdit = useMemo(() => {
        if (isSelectMode && selectedVolumeIds.length > 0) {
            return selectedVolumeIds;
        }

        if (filterKey !== '') {
            return getFilteredVolumeIDs(items, filterKey).map((m) => m.id);
        }

        return items.map((m) => m.id);
    }, [filterKey, isSelectMode, items, selectedVolumeIds]);

    const actionLabel = useMemo(() => {
        if (selectedVolumeIds.length > 0) {
            return translate(labels.selected);
        }
        else if (filterKey !== '') {
            return translate(labels.filtered);
        }

        return translate(labels.all);
    }, [filterKey, labels, selectedVolumeIds.length]);

    const [runMassEditAction] = useMassEditMutation();

    const onPress = useCallback(() => {
        runMassEditAction({
            action: actionKey,
            volumeIds: volumesToEdit,
        });
    }, [actionKey, runMassEditAction, volumesToEdit]);

    return (
        <PageToolbarButton
            label={actionLabel}
            isSpinning={isRunning}
            isDisabled={!totalItems}
            iconName={icon}
            onPress={onPress}
        />
    );
}
