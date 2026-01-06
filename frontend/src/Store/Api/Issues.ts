// IMPORTS

// Redux
import { baseApi } from './base';

// Misc
import snakeify from 'Utilities/Object/snakeify';
import camelize from 'Utilities/Object/camelize';

// Types
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
    filepath: string;
    filename: string;
    prefix: string;
}

export type ThumbnailData = RawThumbnailData & {
    src: string;
};

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
                response.result.map(({ filepath, ...rest }) => ({
                    src: `${window.Kapowarr.urlBase}/api/thumbnail?api_key=${window.Kapowarr.apiKey}&filepath=${filepath.replaceAll('&', '%26')}`,
                    filepath,
                    ...rest,
                })),
        }),

        // POST
        updateBookPages: build.mutation<
            void,
            { fileId: number; newPages: RawThumbnailData[] }
        >({
            query: ({ fileId, newPages: body }) => ({
                method: 'POST',
                url: `files/${fileId}`,
                params: {
                    apiKey: window.Kapowarr.apiKey,
                },
                body,
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
