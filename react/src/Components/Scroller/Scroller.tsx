// IMPORTS

// React
import {
    type ComponentProps,
    type ForwardedRef,
    forwardRef,
    type ReactNode,
    useEffect,
    useImperativeHandle,
    useRef,
} from 'react';

// Redux

// Misc
import { throttle } from 'lodash';

import classNames from 'classnames';

// General Components

// Specific Components

// CSS
import styles from './Scroller.module.css';

// Types
import type { ScrollDirection } from 'Helpers/Props/scrollDirections';

export interface OnScroll {
    scrollLeft: number;
    scrollTop: number;
}

interface ScrollerProps {
    className?: string;
    scrollDirection?: ScrollDirection;
    autoFocus?: boolean;
    autoScroll?: boolean;
    scrollTop?: number;
    initialScrollTop?: number;
    children?: ReactNode;
    style?: ComponentProps<'div'>['style'];
    onScroll?: (payload: OnScroll) => void;
}

// IMPLEMENTATIONS

const Scroller = forwardRef((props: ScrollerProps, ref: ForwardedRef<HTMLDivElement>) => {
    const {
        className,
        autoFocus = false,
        autoScroll = true,
        scrollDirection = 'vertical',
        children,
        scrollTop,
        initialScrollTop,
        onScroll,
        ...otherProps
    } = props;

    const internalRef = useRef<HTMLDivElement>(null);

    useImperativeHandle(ref, () => internalRef.current!, []);

    useEffect(
        () => {
            if (initialScrollTop != null) {
                internalRef.current!.scrollTop = initialScrollTop;
            }
        },
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [],
    );

    useEffect(() => {
        if (scrollTop != null) {
            internalRef.current!.scrollTop = scrollTop;
        }

        if (autoFocus && scrollDirection !== 'none') {
            internalRef.current!.focus({ preventScroll: true });
        }
    }, [autoFocus, scrollDirection, scrollTop]);

    useEffect(() => {
        const div = internalRef.current!;

        const handleScroll = throttle(() => {
            const scrollLeft = div.scrollLeft;
            const scrollTop = div.scrollTop;

            onScroll?.({ scrollLeft, scrollTop });
        }, 10);

        div?.addEventListener('scroll', handleScroll);

        return () => {
            div?.removeEventListener('scroll', handleScroll);
        };
    }, [onScroll]);

    return (
        <div
            {...otherProps}
            ref={internalRef}
            className={classNames(
                className,
                styles.scroller,
                styles[scrollDirection],
                autoScroll && styles.autoScroll,
            )}
            tabIndex={-1}
        >
            {children}
        </div>
    );
});

export default Scroller;
