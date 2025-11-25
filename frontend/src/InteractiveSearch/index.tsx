// IMPORTS

// React
import { useCallback, useEffect, useMemo, useState } from 'react';

// Redux
import { useRootSelector } from 'Store/createAppStore';

import { useFetchQueueDetails } from 'Store/Api/Queue';

import {
    useLazyManualSearchQuery,
    useLibgenFileSearchMutation,
} from 'Store/Api/Command';

// Misc
import { icons, inputTypes, kinds } from 'Helpers/Props';

import { getErrorMessage } from 'Utilities/Object/error';

import translate from 'Utilities/String/translate';

// General Components
import Alert from 'Components/Alert';
import Form from 'Components/Form/Form';
import FormGroup from 'Components/Form/FormGroup';
import FormInputButton from 'Components/Form/FormInputButton';
import FormInputGroup from 'Components/Form/FormInputGroup';
import FormLabel from 'Components/Form/FormLabel';
import Icon from 'Components/Icon';
import LoadingIndicator from 'Components/Loading/LoadingIndicator';
import SortedTable from 'Components/Table/SortedTable';

// Specific Components
import InteractiveSearchRow from './InteractiveSearchRow';
import InteractiveSearchTableOptions from './TableOptions';
import InteractiveSearchIssueTableOptions from './IssueTableOptions';

// CSS
import styles from './index.module.css';

// Types
import type { InteractiveSearchPayload, SearchResult } from 'typings/Search';

import type { AnyError } from 'typings/Api';
import type { InputChanged } from 'typings/Inputs';

export interface SearchResultItem extends SearchResult {
    id: number;
}

export interface InteractiveSearchProps {
    searchPayload: InteractiveSearchPayload;
}

interface SearchProps extends InteractiveSearchProps {
    isFetching: boolean;
    isPopulated: boolean;
    error: AnyError | undefined;
    errorMessage: string;
    items: SearchResultItem[];
    totalItems: number;
}

// IMPLEMENTATIONS

function weighIssueNumber(
    issueNumber: number | [number, number] | null,
    lastIssueNumber: number,
): number {
    if (Array.isArray(issueNumber)) {
        return lastIssueNumber + issueNumber[0];
    }

    if (typeof issueNumber !== 'number') {
        return lastIssueNumber * 2;
    }

    return issueNumber;
}

function InternalSearch({
    isFetching,
    isPopulated,
    error,
    errorMessage,
    items,
    totalItems,
    searchPayload,
}: SearchProps) {
    const { columns } = useRootSelector(
        (state) => state.tableOptions.interactiveSearch,
    );

    const lastIssueNumber = useMemo(() => {
        return Math.max(
            ...items
                .map((item) =>
                    Array.isArray(item.issueNumber)
                        ? item.issueNumber[1]
                        : item.issueNumber,
                )
                .filter((issueNumber) => issueNumber !== null),
        );
    }, [items]);

    return (
        <div>
            {isFetching ? <LoadingIndicator /> : null}

            {!isFetching && error ? (
                <div>
                    {errorMessage
                        ? translate(
                              'InteractiveSearchResultsVolumeFailedErrorMessage',
                              {
                                  message:
                                      errorMessage.charAt(0).toLowerCase() +
                                      errorMessage.slice(1),
                              },
                          )
                        : translate('IssueSearchResultsLoadError')}
                </div>
            ) : null}

            {!isFetching && isPopulated && !totalItems ? (
                <Alert kind={kinds.INFO}>{translate('NoResultsFound')}</Alert>
            ) : null}

            {!isFetching && isPopulated ? (
                <SortedTable
                    tableName="interactiveSearch"
                    columns={columns}
                    items={items}
                    itemRenderer={(item) => (
                        <InteractiveSearchRow
                            key={item.id}
                            columns={columns}
                            result={item}
                            items={items}
                            searchPayload={searchPayload}
                        />
                    )}
                    predicates={{
                        match: (a, b) =>
                            parseInt(a.rank.join('')) -
                            parseInt(b.rank.join('')),

                        issueNumber: (a, b) =>
                            weighIssueNumber(a.issueNumber, lastIssueNumber) -
                            weighIssueNumber(b.issueNumber, lastIssueNumber),

                        matchRejections: (a, b) =>
                            a.matchRejections.length - b.matchRejections.length,
                    }}
                    tableProps={
                        'issues' in searchPayload
                            ? {
                                  optionsComponent:
                                      InteractiveSearchTableOptions,
                              }
                            : {
                                  optionsComponent:
                                      InteractiveSearchIssueTableOptions,
                              }
                    }
                />
            ) : null}

            {!!totalItems && isPopulated && !items.length ? (
                <Alert kind={kinds.WARNING}>
                    {translate('AllResultsAreHiddenByTheAppliedFilter')}
                </Alert>
            ) : null}

            {totalItems !== items.length && items.length ? (
                <div className={styles.filteredMessage}>
                    {translate('SomeResultsAreHiddenByTheAppliedFilter')}
                </div>
            ) : null}
        </div>
    );
}

export function LibgenFileSearch({ searchPayload }: InteractiveSearchProps) {
    const [search, searchProps] = useLibgenFileSearchMutation({
        selectFromResult: ({ isLoading, isUninitialized, error, data }) => ({
            isFetching: isLoading,
            isPopulated: !isUninitialized,
            error,
            errorMessage: getErrorMessage(error),
            items: (data?.map((item, id) => ({ ...item, id })) ??
                []) as SearchResultItem[],
            totalItems: data?.length ?? 0,
        }),
    });

    const [libgenFileUrl, setLibgenFileUrl] = useState('');

    const onUrlChange = useCallback(
        ({ value }: InputChanged<'url', string>) => {
            setLibgenFileUrl(value);
        },
        [],
    );

    const startSearch = useCallback(() => {
        search({
            url: libgenFileUrl,
            ...searchPayload,
        });
    }, [searchPayload, libgenFileUrl, search]);

    if (!searchProps.isPopulated) {
        return (
            <Form>
                <FormGroup>
                    <FormLabel>{translate('LibgenFileSearch')}</FormLabel>

                    <FormInputGroup
                        type={inputTypes.TEXT}
                        name="url"
                        value={libgenFileUrl}
                        helpText={translate('LibgenFileSearchHelpText')}
                        buttons={[
                            <FormInputButton
                                title={translate('Search')}
                                onPress={startSearch}
                            >
                                <Icon name={icons.SEARCH} />
                            </FormInputButton>,
                        ]}
                        onChange={onUrlChange}
                        onSubmit={startSearch}
                    />
                </FormGroup>
            </Form>
        );
    }

    return <InternalSearch searchPayload={searchPayload} {...searchProps} />;
}

function useQueueInfo({ searchPayload }: InteractiveSearchProps): number[] {
    const { queue } = useFetchQueueDetails({
        volumeId: 'volumeId' in searchPayload ? searchPayload.volumeId : -1,
    });

    if (!('volumeId' in searchPayload)) {
        return [];
    }

    return queue.map((item) => item.issueId).filter((id) => id !== null);
}

export default function InteractiveSearch({
    searchPayload,
}: InteractiveSearchProps) {
    const [search, { data, ...searchProps }] = useLazyManualSearchQuery({
        selectFromResult: ({ isFetching, isUninitialized, error, data }) => {
            const filteredData: SearchResultItem[] =
                data?.map((item, id) => ({ ...item, id })) ?? [];

            return {
                isFetching,
                isPopulated: !isUninitialized,
                error,
                errorMessage: getErrorMessage(error),
                data: filteredData,
                totalItems: filteredData.length,
            };
        },
    });

    useEffect(() => {
        search(searchPayload);
        // only fetch on mount
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const { hideDownloaded, hideDownloading, hideUnmonitored, hideUnmatched } =
        useRootSelector((state) => state.tableOptions.interactiveSearch);

    const downloadingIds = useQueueInfo({ searchPayload });

    const issues = useMemo(() => {
        const volumeIssues =
            'issues' in searchPayload ? searchPayload.issues : undefined;

        // Whether to filter the results
        if (
            !volumeIssues ||
            (!hideDownloaded && !hideUnmonitored && !hideDownloading)
        ) {
            return undefined;
        }

        let result = volumeIssues;

        if (hideDownloaded) {
            result = result.filter((issue) => issue.files.length === 0);
        }

        if (hideDownloading) {
            result = result.filter(
                (issue) => !downloadingIds.includes(issue.id),
            );
        }

        if (hideUnmonitored) {
            result = result.filter((issue) => issue.monitored);
        }

        return result.map((issue) => issue.calculatedIssueNumber);
    }, [
        downloadingIds,
        hideDownloaded,
        hideDownloading,
        hideUnmonitored,
        searchPayload,
    ]);

    const items = useMemo(() => {
        const items = hideUnmatched ? data.filter((item) => item.match) : data;

        if (!issues) {
            return items;
        }

        return items.filter((item) => {
            const issueNumber = item.issueNumber;

            return Array.isArray(issueNumber)
                ? issues.some(
                      (id) => id >= issueNumber[0] && id <= issueNumber[1],
                  )
                : issues.includes(issueNumber ?? -1);
        });
    }, [data, hideUnmatched, issues]);

    return (
        <InternalSearch
            searchPayload={searchPayload}
            items={items}
            {...searchProps}
        />
    );
}
