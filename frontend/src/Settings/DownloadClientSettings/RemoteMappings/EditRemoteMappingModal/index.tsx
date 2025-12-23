// IMPORTS

// Misc
import { sizes } from 'Helpers/Props';

// General Components
import Modal from 'Components/Modal/Modal';

// Specific Components
import EditRemoteMappingModalContent from './ModalContent';

// Types
import type { EditRemoteMappingModalContentProps } from './ModalContent';

interface EditRemoteMappingModalProps extends EditRemoteMappingModalContentProps {
    isOpen: boolean;
}

// IMPLEMENTATIONS

export default function EditRemoteMappingModal({
    isOpen,
    onModalClose,
    ...otherProps
}: EditRemoteMappingModalProps) {
    return (
        <Modal size={sizes.MEDIUM} isOpen={isOpen} onModalClose={onModalClose}>
            <EditRemoteMappingModalContent
                {...otherProps}
                onModalClose={onModalClose}
            />
        </Modal>
    );
}
