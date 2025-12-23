// IMPORTS

// React
import {
    type FormEvent,
    type KeyboardEvent,
    type SyntheticEvent,
    useCallback,
    useEffect,
    useMemo,
    useRef,
    useState,
} from 'react';

import Autosuggest from 'react-autosuggest';

// Redux
import { useGetVolumesQuery } from 'Store/Api/Volumes';

// Misc
import { icons } from 'Helpers/Props';

import translate from 'Utilities/String/translate';

// Hooks
import { useDebouncedCallback } from 'use-debounce';
import { useNavigate } from 'react-router';

import useKeyboardShortcuts from 'Helpers/Hooks/useKeyboardShortcuts';

// General Components
import Icon from 'Components/Icon';
import LoadingIndicator from 'Components/Loading/LoadingIndicator';

// Specific Components
import VolumeSearchResult from '../VolumeSearchResult';

// CSS
import styles from './index.module.css';

// Types
import type { ExtendedKeyboardEvent } from 'mousetrap';
import type { Volume } from 'Volume/Volume';

interface Match {
    key: string;
    refIndex: number;
}

interface AddNewVolumeSuggestion {
    type: 'addNew';
    title: string;
}

export interface SuggestedVolume extends Pick<
    Volume,
    'title' | 'id' | 'comicvineId'
> {
    firstCharacter: string;
}

interface VolumeSuggestion {
    title: string;
    indices: number[];
    item: SuggestedVolume;
    matches: Match[];
    refIndex: number;
}

interface Section {
    title: string;
    loading?: boolean;
    suggestions: VolumeSuggestion[] | AddNewVolumeSuggestion[];
}

// IMPLEMENTATIONS

const ADD_NEW_TYPE = 'addNew';

export default function VolumeSearchInput() {
    const navigate = useNavigate();

    const { volumes } = useGetVolumesQuery(undefined, {
        selectFromResult: ({ data: allVolumes = [] }) => {
            return {
                volumes: allVolumes.map((volume): SuggestedVolume => {
                    const { title, id, comicvineId } = volume;

                    return {
                        title,
                        id,
                        comicvineId,
                        firstCharacter: title.charAt(0).toLowerCase(),
                    };
                }),
            };
        },
    });

    const { bindShortcut, unbindShortcut } = useKeyboardShortcuts();

    const [value, setValue] = useState('');
    const [requestLoading, setRequestLoading] = useState(false);
    const [suggestions, setSuggestions] = useState<VolumeSuggestion[]>([]);
    const [isLoading, setIsLoading] = useState(false);

    const autosuggestRef = useRef<Autosuggest>(null);
    const inputRef = useRef<HTMLInputElement>(null);
    const worker = useRef<Worker | null>(null);
    const requestValue = useRef<string | null>(null);

    const suggestionGroups = useMemo(() => {
        const result: Section[] = [];

        if (suggestions.length || isLoading) {
            result.push({
                title: translate('ExistingVolume'),
                loading: isLoading,
                suggestions,
            });
        }

        result.push({
            title: translate('AddNewVolume'),
            suggestions: [
                {
                    type: ADD_NEW_TYPE,
                    title: value,
                },
            ],
        });

        return result;
    }, [isLoading, suggestions, value]);

    const handleSuggestionsReceived = useCallback(
        (message: {
            data: { value: string; suggestions: VolumeSuggestion[] };
        }) => {
            const { value, suggestions } = message.data;

            if (!isLoading) {
                requestValue.current = null;
                setRequestLoading(false);
            }
            else if (value === requestValue.current) {
                setSuggestions(suggestions);
                requestValue.current = null;
                setRequestLoading(false);
                setIsLoading(false);
            }
            else {
                setSuggestions(suggestions);
                setRequestLoading(true);

                const payload = {
                    value: requestValue,
                    volumes,
                };

                worker.current?.postMessage(payload);
            }
        },
        [isLoading, volumes],
    );

    const requestSuggestions = useDebouncedCallback((value: string) => {
        if (!isLoading) {
            return;
        }

        requestValue.current = value;
        setRequestLoading(true);

        if (!requestLoading) {
            const payload = {
                value,
                volumes,
            };

            worker.current?.postMessage(payload);
        }
    }, 250);

    const reset = useCallback(() => {
        setValue('');
        setSuggestions([]);
        setIsLoading(false);
    }, []);

    const focusInput = useCallback((event: ExtendedKeyboardEvent) => {
        event.preventDefault();
        inputRef.current?.focus();
    }, []);

    const getSectionSuggestions = useCallback((section: Section) => {
        return section.suggestions;
    }, []);

    const renderSectionTitle = useCallback((section: Section) => {
        return (
            <div className={styles.sectionTitle}>
                {section.title}

                {section.loading && (
                    <LoadingIndicator
                        className={styles.loading}
                        rippleClassName={styles.ripple}
                        size={20}
                    />
                )}
            </div>
        );
    }, []);

    const getSuggestionValue = useCallback(({ title }: { title: string }) => {
        return title;
    }, []);

    const renderSuggestion = useCallback(
        (
            item: AddNewVolumeSuggestion | VolumeSuggestion,
            { query }: { query: string },
        ) => {
            if ('type' in item) {
                return (
                    <div className={styles.addNewVolumeSuggestion}>
                        {translate('SearchForQuery', { query })}
                    </div>
                );
            }

            return (
                <VolumeSearchResult {...item.item} match={item.matches[0]} />
            );
        },
        [],
    );

    const handleChange = useCallback(
        (
            _event: FormEvent<HTMLElement>,
            {
                newValue,
                method,
            }: {
                newValue: string;
                method: 'down' | 'up' | 'escape' | 'enter' | 'click' | 'type';
            },
        ) => {
            if (method === 'up' || method === 'down') {
                return;
            }

            setValue(newValue);
        },
        [],
    );

    const handleKeyDown = useCallback(
        (event: KeyboardEvent<HTMLElement>) => {
            if (event.shiftKey || event.altKey || event.ctrlKey) {
                return;
            }

            if (event.key === 'Escape') {
                reset();
                return;
            }

            if (event.key !== 'Tab' && event.key !== 'Enter') {
                return;
            }

            if (!autosuggestRef.current) {
                return;
            }

            const { highlightedSectionIndex, highlightedSuggestionIndex } =
                autosuggestRef.current.state;

            if (!suggestions.length || highlightedSectionIndex) {
                navigate(`/add/new?term=${encodeURIComponent(value)}`);

                inputRef.current?.blur();
                reset();

                return;
            }

            // If a suggestion is not selected go to the first volume,
            // otherwise go to the selected volume.
            const selectedSuggestion = !highlightedSuggestionIndex
                ? suggestions[0]
                : suggestions[highlightedSuggestionIndex];

            navigate(`/volumes/${selectedSuggestion.item.id}`);

            inputRef.current?.blur();
            reset();
        },
        [value, suggestions, reset, navigate],
    );

    const handleBlur = useCallback(() => {
        reset();
    }, [reset]);

    const handleSuggestionsFetchRequested = useCallback(
        ({ value }: { value: string }) => {
            setIsLoading(true);

            requestSuggestions(value);
        },
        [requestSuggestions],
    );

    const handleSuggestionsClearRequested = useCallback(() => {
        setSuggestions([]);
        setIsLoading(false);
    }, []);

    const handleSuggestionSelected = useCallback(
        (
            _event: SyntheticEvent,
            {
                suggestion,
            }: { suggestion: VolumeSuggestion | AddNewVolumeSuggestion },
        ) => {
            if ('type' in suggestion) {
                navigate(`/add/new?term=${encodeURIComponent(value)}`);
            }
            else {
                setValue('');
                navigate(`/volumes/${suggestion.item.id}`);
            }
        },
        [value, navigate],
    );

    const inputProps = {
        ref: inputRef,
        className: styles.input,
        name: 'volumeSearch',
        value,
        placeholder: translate('Search'),
        autoComplete: 'off',
        spellCheck: false,
        onChange: handleChange,
        onKeyDown: handleKeyDown,
        onBlur: handleBlur,
    };

    const theme = {
        container: styles.container,
        containerOpen: styles.containerOpen,
        suggestionsContainer: styles.volumeContainer,
        suggestionsList: styles.list,
        suggestion: styles.listItem,
        suggestionHighlighted: styles.highlighted,
    };

    useEffect(() => {
        worker.current = new Worker(
            `${window.Kapowarr.urlBase}/static/js/fuse.worker.js`,
            {
                type: 'module',
            },
        );

        return () => {
            if (worker.current) {
                worker.current.terminate();
                worker.current = null;
            }
        };
    }, []);

    useEffect(() => {
        worker.current?.addEventListener(
            'message',
            handleSuggestionsReceived,
            false,
        );

        return () => {
            if (worker.current) {
                worker.current.removeEventListener(
                    'message',
                    handleSuggestionsReceived,
                    false,
                );
            }
        };
    }, [handleSuggestionsReceived]);

    useEffect(() => {
        bindShortcut('focusVolumeSearchInput', focusInput);

        return () => {
            unbindShortcut('focusVolumeSearchInput');
        };
    }, [bindShortcut, unbindShortcut, focusInput]);

    return (
        <div className={styles.wrapper}>
            <Icon name={icons.SEARCH} />

            <Autosuggest
                ref={autosuggestRef}
                inputProps={inputProps}
                theme={theme}
                focusInputOnSuggestionClick={false}
                multiSection={true}
                suggestions={suggestionGroups}
                getSectionSuggestions={getSectionSuggestions}
                renderSectionTitle={renderSectionTitle}
                getSuggestionValue={getSuggestionValue}
                renderSuggestion={renderSuggestion}
                onSuggestionSelected={handleSuggestionSelected}
                onSuggestionsFetchRequested={handleSuggestionsFetchRequested}
                onSuggestionsClearRequested={handleSuggestionsClearRequested}
            />
        </div>
    );
}
