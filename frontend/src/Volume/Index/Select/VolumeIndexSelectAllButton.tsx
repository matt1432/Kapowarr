// IMPORTS

// React
import { useCallback } from 'react';

// Misc
import { useSelect } from 'App/SelectContext';
import { icons } from 'Helpers/Props';

import translate from 'Utilities/String/translate';

// General Components
import PageToolbarButton, {
    type PageToolbarButtonProps,
} from 'Components/Page/Toolbar/PageToolbarButton';

// Types
interface VolumeIndexSelectAllButtonProps extends Omit<
    PageToolbarButtonProps,
    'iconName'
> {
    isSelectMode: boolean;
}

// IMPLEMENTATIONS

export default function VolumeIndexSelectAllButton({
    isSelectMode,
    overflowComponent,
}: VolumeIndexSelectAllButtonProps) {
    const [selectState, selectDispatch] = useSelect();
    const { allSelected, allUnselected } = selectState;

    let icon = icons.SQUARE_MINUS;

    if (allSelected) {
        icon = icons.CHECK_SQUARE;
    }
    else if (allUnselected) {
        icon = icons.SQUARE;
    }

    const onPress = useCallback(() => {
        selectDispatch({
            type: allSelected ? 'unselectAll' : 'selectAll',
        });
    }, [allSelected, selectDispatch]);

    return isSelectMode ? (
        <PageToolbarButton
            label={
                allSelected ? translate('UnselectAll') : translate('SelectAll')
            }
            iconName={icon}
            overflowComponent={overflowComponent}
            onPress={onPress}
        />
    ) : null;
}
