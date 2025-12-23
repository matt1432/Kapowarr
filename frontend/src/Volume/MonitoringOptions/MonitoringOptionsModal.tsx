// IMPORTS

// General Components
import Modal from 'Components/Modal/Modal';

// Specific Components
import MonitoringOptionsModalContent, {
    type MonitoringOptionsModalContentProps,
} from './MonitoringOptionsModalContent';

// Types
interface MonitoringOptionsModalProps extends MonitoringOptionsModalContentProps {
    isOpen: boolean;
}

// IMPLEMENTATIONS

export default function MonitoringOptionsModal({
    isOpen,
    onModalClose,
    ...otherProps
}: MonitoringOptionsModalProps) {
    return (
        <Modal isOpen={isOpen} onModalClose={onModalClose}>
            <MonitoringOptionsModalContent
                {...otherProps}
                onModalClose={onModalClose}
            />
        </Modal>
    );
}
