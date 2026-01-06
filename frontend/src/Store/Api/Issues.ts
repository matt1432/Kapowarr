// IMPORTS

// Redux
import { baseApi } from './base';

// Misc
import snakeify from 'Utilities/Object/snakeify';
import camelize from 'Utilities/Object/camelize';

// Types
import type { CamelCasedPropertiesDeep } from 'type-fest';

import type { IssueData, RawIssueData } from 'Issue/Issue';

export interface ToggleIssueParams {
    issueId: number;
    monitored: boolean;
}

export interface UpdateIssueParams {
    issueId: number;
    monitored?: boolean;
    title?: string;
    description?: string;
    calledFrom?: string;
}

export interface RawThumbnailData {
    folder_name: string;
    full_path: string;
    prefix: string;
    current_filename: string;
    new_filename: string;
}

export type ThumbnailData = CamelCasedPropertiesDeep<
    RawThumbnailData & {
        src: string;
    }
>;

// IMPLEMENTATIONS

const extendedApi = baseApi.injectEndpoints({
    endpoints: (build) => ({
        // GET
        getIssue: build.query<IssueData, { issueId: number }>({
            query: ({ issueId }) => ({
                url: `issues/${issueId}`,
                params: {
                    apiKey: window.Kapowarr.apiKey,
                },
            }),

            transformResponse: (response: { result: RawIssueData }) =>
                camelize(response.result),
        }),

        getThumbnailURLs: build.mutation<
            ThumbnailData[],
            { issueId: number; filepath: string; refresh?: boolean }
        >({
            query: ({ issueId, ...params }) => ({
                method: 'GET',
                url: `issues/${issueId}/thumbnails`,
                params: {
                    ...params,
                    apiKey: window.Kapowarr.apiKey,
                },
            }),

            transformResponse: (response: { result: RawThumbnailData[] }) =>
                response.result.map(({ full_path, ...rest }) =>
                    camelize({
                        src: `${window.Kapowarr.urlBase}/api/thumbnail?api_key=${window.Kapowarr.apiKey}&filepath=${full_path.replaceAll('&', '%26')}`,
                        full_path,
                        ...rest,
                    }),
                ),
        }),

        // POST
        updateBookPages: build.mutation<
            void,
            { fileId: number; newPages: ThumbnailData[] }
        >({
            query: ({ fileId, newPages }) => ({
                method: 'POST',
                url: `files/${fileId}`,
                params: {
                    apiKey: window.Kapowarr.apiKey,
                },
                body: snakeify(newPages),
            }),
        }),

        // PUT
        updateIssue: build.mutation<void, UpdateIssueParams>({
            query: ({ issueId, ...body }) => ({
                method: 'PUT',
                url: `issues/${issueId}`,
                params: {
                    apiKey: window.Kapowarr.apiKey,
                },
                body: snakeify(body),
            }),
        }),
    }),
});

export const {
    useGetIssueQuery,
    useGetThumbnailURLsMutation,
    useLazyGetIssueQuery,
    useUpdateBookPagesMutation,
    useUpdateIssueMutation,
} = extendedApi;
