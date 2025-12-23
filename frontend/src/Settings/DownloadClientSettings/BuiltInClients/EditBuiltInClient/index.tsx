// IMPORTS

// Misc
import { sizes } from 'Helpers/Props';

// General Components
import Modal from 'Components/Modal/Modal';

// Specific Components
import EditBuiltInClientModalContent from './EditBuiltInClientModalContent';

// Types
import type { EditBuiltInClientModalContentProps } from './EditBuiltInClientModalContent';

interface EditBuiltInClientModalProps extends EditBuiltInClientModalContentProps {
    isOpen: boolean;
}

// IMPLEMENTATIONS

export default function EditBuiltInClientModal({
    isOpen,
    onModalClose,
    ...otherProps
}: EditBuiltInClientModalProps) {
    return (
        <Modal size={sizes.MEDIUM} isOpen={isOpen} onModalClose={onModalClose}>
            <EditBuiltInClientModalContent
                {...otherProps}
                onModalClose={onModalClose}
            />
        </Modal>
    );
}
