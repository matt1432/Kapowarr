import classNames from 'classnames';
import { type ReactNode } from 'react';
import styles from './EnhancedSelectInputSelectedValue.module.css';

interface EnhancedSelectInputSelectedValueProps {
    className?: string;
    children: ReactNode;
    isDisabled?: boolean;
}

function EnhancedSelectInputSelectedValue({
    className = styles.selectedValue,
    children,
    isDisabled = false,
}: EnhancedSelectInputSelectedValueProps) {
    return <div className={classNames(className, isDisabled && styles.isDisabled)}>{children}</div>;
}

export default EnhancedSelectInputSelectedValue;
