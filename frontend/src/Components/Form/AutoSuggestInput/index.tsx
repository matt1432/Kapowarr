// IMPORTS

// React
import {
    type FocusEvent,
    type FormEvent,
    type KeyboardEvent,
    type KeyboardEventHandler,
    type MutableRefObject,
    type ReactNode,
    type Ref,
    type SyntheticEvent,
    useCallback,
    useEffect,
    useRef,
    useState,
} from 'react';

import Autosuggest, {
    type AutosuggestPropsBase,
    type BlurEvent,
    type ChangeEvent,
    type RenderInputComponentProps,
    type RenderSuggestionsContainerParams,
} from 'react-autosuggest';
import { autoUpdate, flip, size, useFloating } from '@floating-ui/react-dom';

// Misc
import classNames from 'classnames';

// CSS
import styles from './index.module.css';

// Types
import type { InputChanged } from 'typings/Inputs';

interface AutoSuggestInputProps<K extends string, T> extends Omit<
    AutosuggestPropsBase<T>,
    'renderInputComponent' | 'inputProps'
> {
    forwardedRef?: MutableRefObject<Autosuggest<T> | null>;
    className?: string;
    inputContainerClassName?: string;
    name: K;
    value?: string;
    placeholder?: string;
    suggestions: T[];
    hasError?: boolean;
    hasWarning?: boolean;
    enforceMaxHeight?: boolean;
    maxHeight?: number;
    renderInputComponent?: (
        inputProps: RenderInputComponentProps,
        ref: Ref<HTMLDivElement>,
    ) => ReactNode;
    onInputChange: (
        event: FormEvent<HTMLElement>,
        params: ChangeEvent,
    ) => unknown;
    onInputKeyDown?: KeyboardEventHandler<HTMLElement>;
    onInputFocus?: (event: SyntheticEvent) => unknown;
    onInputBlur: (
        event: FocusEvent<HTMLElement>,
        params?: BlurEvent<T>,
    ) => unknown;
    onChange?: (change: InputChanged<K, string>) => unknown;
}

// IMPLEMENTATIONS

export default function AutoSuggestInput<T, K extends string>({
    forwardedRef,
    className = styles.input,
    inputContainerClassName = styles.inputContainer,
    name,
    value = '',
    placeholder,
    suggestions,
    enforceMaxHeight = true,
    hasError,
    hasWarning,
    maxHeight = 200,
    getSuggestionValue,
    renderSuggestion,
    renderInputComponent,
    onInputChange,
    onInputKeyDown,
    onInputFocus,
    onInputBlur,
    onSuggestionsFetchRequested,
    onSuggestionsClearRequested,
    onSuggestionSelected,
    ...otherProps
}: AutoSuggestInputProps<K, T>) {
    const updater = useRef<(() => void) | null>(null);
    const [previousSuggestions, setPreviousSuggestions] = useState(suggestions);
    if (suggestions !== previousSuggestions) {
        setPreviousSuggestions(suggestions);
    }

    const { refs, floatingStyles } = useFloating({
        middleware: [
            flip({
                crossAxis: false,
                mainAxis: true,
            }),
            size({
                apply({ availableHeight, elements, rects }) {
                    Object.assign(elements.floating.style, {
                        minWidth: `${rects.reference.width}px`,
                        maxHeight: `${Math.max(0, availableHeight)}px`,
                    });
                },
            }),
        ],
        placement: 'bottom-start',
        whileElementsMounted: autoUpdate,
    });

    const createRenderInputComponent = useCallback(
        (inputProps: RenderInputComponentProps) => {
            if (renderInputComponent) {
                return renderInputComponent(inputProps, refs.setReference);
            }

            return (
                <div ref={refs.setReference}>
                    <input {...inputProps} />
                </div>
            );
        },
        [refs.setReference, renderInputComponent],
    );

    const renderSuggestionsContainer = useCallback(
        ({ containerProps, children }: RenderSuggestionsContainerParams) => {
            return (
                <div
                    ref={refs.setFloating}
                    style={floatingStyles}
                    className={
                        children ? styles.suggestionsContainerOpen : undefined
                    }
                >
                    <div
                        {...containerProps}
                        style={{
                            maxHeight: enforceMaxHeight ? maxHeight : undefined,
                        }}
                    >
                        {children}
                    </div>
                </div>
            );
        },
        [enforceMaxHeight, floatingStyles, maxHeight, refs.setFloating],
    );

    const handleInputKeyDown = useCallback(
        (event: KeyboardEvent<HTMLElement>) => {
            if (
                event.key === 'Tab' &&
                suggestions.length &&
                suggestions[0] !== value
            ) {
                event.preventDefault();

                if (value) {
                    onSuggestionSelected?.(event, {
                        suggestion: suggestions[0],
                        suggestionValue: value,
                        suggestionIndex: 0,
                        sectionIndex: null,
                        method: 'enter',
                    });
                }
            }
        },
        [value, suggestions, onSuggestionSelected],
    );

    const inputProps = {
        className: classNames(
            className,
            hasError && styles.hasError,
            hasWarning && styles.hasWarning,
        ),
        name,
        value,
        placeholder,
        autoComplete: 'off',
        spellCheck: false,
        onChange: onInputChange,
        onKeyDown: onInputKeyDown || handleInputKeyDown,
        onFocus: onInputFocus,
        onBlur: onInputBlur,
    };

    const theme = {
        container: inputContainerClassName,
        containerOpen: styles.suggestionsContainerOpen,
        suggestionsContainer: styles.suggestionsContainer,
        suggestionsList: styles.suggestionsList,
        suggestion: styles.suggestion,
        suggestionHighlighted: styles.suggestionHighlighted,
    };

    useEffect(() => {
        if (updater.current && suggestions !== previousSuggestions) {
            updater.current();
        }
    }, [suggestions, previousSuggestions]);

    return (
        <Autosuggest
            {...otherProps}
            ref={forwardedRef}
            id={name}
            inputProps={inputProps}
            theme={theme}
            suggestions={suggestions}
            getSuggestionValue={getSuggestionValue}
            renderInputComponent={createRenderInputComponent}
            renderSuggestionsContainer={renderSuggestionsContainer}
            renderSuggestion={renderSuggestion}
            onSuggestionSelected={onSuggestionSelected}
            onSuggestionsFetchRequested={onSuggestionsFetchRequested}
            onSuggestionsClearRequested={onSuggestionsClearRequested}
        />
    );
}
