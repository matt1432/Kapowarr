import Modal from 'Components/Modal/Modal';
import FileBrowserModalContent, {
    type FileBrowserModalContentProps,
} from './FileBrowserModalContent';
import styles from './FileBrowserModal.module.css';

interface FileBrowserModalProps extends FileBrowserModalContentProps {
    isOpen: boolean;
    onModalClose: () => void;
}

function FileBrowserModal(props: FileBrowserModalProps) {
    const { isOpen, onModalClose, ...otherProps } = props;

    return (
        <Modal className={styles.modal} isOpen={isOpen} onModalClose={onModalClose}>
            <FileBrowserModalContent {...otherProps} onModalClose={onModalClose} />
        </Modal>
    );
}

export default FileBrowserModal;
