// IMPORTS

// Misc
import { sizes } from 'Helpers/Props';

// General Components
import Modal from 'Components/Modal/Modal';

// Specific Components
import EditDownloadClientModalContent from './EditDownloadClientModalContent';

// Types
import type { EditDownloadClientModalContentProps } from './EditDownloadClientModalContent';

interface EditDownloadClientModalProps extends EditDownloadClientModalContentProps {
    isOpen: boolean;
}

// IMPLEMENTATIONS

export default function EditDownloadClientModal({
    isOpen,
    onModalClose,
    ...otherProps
}: EditDownloadClientModalProps) {
    return (
        <Modal size={sizes.MEDIUM} isOpen={isOpen} onModalClose={onModalClose}>
            <EditDownloadClientModalContent
                {...otherProps}
                onModalClose={onModalClose}
            />
        </Modal>
    );
}
