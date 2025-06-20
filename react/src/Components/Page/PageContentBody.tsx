import { type ForwardedRef, forwardRef, type ReactNode, useCallback } from 'react';
import Scroller, { type OnScroll } from 'Components/Scroller/Scroller';
import { isLocked } from 'Utilities/scrollLock';
import styles from './PageContentBody.css';

interface PageContentBodyProps {
    className?: string;
    innerClassName?: string;
    children: ReactNode;
    initialScrollTop?: number;
    onScroll?: (payload: OnScroll) => void;
}

const PageContentBody = forwardRef(
    (props: PageContentBodyProps, ref: ForwardedRef<HTMLDivElement>) => {
        const {
            className = styles.contentBody,
            innerClassName = styles.innerContentBody,
            children,
            onScroll,
            ...otherProps
        } = props;

        const onScrollWrapper = useCallback(
            (payload: OnScroll) => {
                if (onScroll && !isLocked()) {
                    onScroll(payload);
                }
            },
            [onScroll],
        );

        return (
            <Scroller
                ref={ref}
                {...otherProps}
                className={className}
                scrollDirection="vertical"
                onScroll={onScrollWrapper}
            >
                <div className={innerClassName}>{children}</div>
            </Scroller>
        );
    },
);

export default PageContentBody;
