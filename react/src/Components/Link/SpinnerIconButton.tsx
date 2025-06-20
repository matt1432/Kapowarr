import { type IconName } from 'Components/Icon';
import { icons } from 'Helpers/Props';
import IconButton, { type IconButtonProps } from './IconButton';

interface SpinnerIconButtonProps extends IconButtonProps {
    spinningName?: IconName;
}

function SpinnerIconButton({
    name,
    spinningName = icons.SPINNER,
    isDisabled = false,
    isSpinning = false,
    ...otherProps
}: SpinnerIconButtonProps) {
    return (
        <IconButton
            name={isSpinning ? spinningName || name : name}
            isDisabled={isDisabled || isSpinning}
            isSpinning={isSpinning}
            {...otherProps}
        />
    );
}

export default SpinnerIconButton;
