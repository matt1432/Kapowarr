import { useCallback } from 'react';
import { useSelect } from 'App/SelectContext';
import { type IconName } from 'Components/Icon';
import PageToolbarOverflowMenuItem from 'Components/Page/Toolbar/PageToolbarOverflowMenuItem';

interface VolumesIndexSelectModeMenuItemProps {
    label: string;
    iconName: IconName;
    isSelectMode: boolean;
    onPress: () => void;
}

function VolumesIndexSelectModeMenuItem(props: VolumesIndexSelectModeMenuItemProps) {
    const { label, iconName, isSelectMode, onPress } = props;
    const [, selectDispatch] = useSelect();

    const onPressWrapper = useCallback(() => {
        if (isSelectMode) {
            selectDispatch({
                type: 'reset',
            });
        }

        onPress();
    }, [isSelectMode, onPress, selectDispatch]);

    return (
        <PageToolbarOverflowMenuItem label={label} iconName={iconName} onPress={onPressWrapper} />
    );
}

export default VolumesIndexSelectModeMenuItem;
