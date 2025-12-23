// IMPORTS

// General Components
import Modal from 'Components/Modal/Modal';

// Specific Components
import AddDownloadClientModalContent from './AddDownloadClientModalContent';

// Types
import type { AddDownloadClientModalContentProps } from './AddDownloadClientModalContent';

interface AddDownloadClientModalProps extends AddDownloadClientModalContentProps {
    isOpen: boolean;
}

// IMPLEMENTATIONS

function AddDownloadClientModal({
    isOpen,
    onModalClose,
    ...otherProps
}: AddDownloadClientModalProps) {
    return (
        <Modal isOpen={isOpen} onModalClose={onModalClose}>
            <AddDownloadClientModalContent
                {...otherProps}
                onModalClose={onModalClose}
            />
        </Modal>
    );
}

export default AddDownloadClientModal;
