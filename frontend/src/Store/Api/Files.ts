// IMPORTS

// Redux
import { baseApi } from './base';

// Misc
import snakeify from 'Utilities/Object/snakeify';
import camelize from 'Utilities/Object/camelize';

// Types
import type { FileData, RawFileData } from 'Issue/Issue';

export interface UpdateFileParams {
    fileId: number;
    releaser?: string;
    scanType?: string;
    resolution?: string;
    dpi?: string;
    notes?: string;
}

// IMPLEMENTATIONS

const extendedApi = baseApi.injectEndpoints({
    endpoints: (build) => ({
        // GET
        getFile: build.query<FileData, { fileId: number }>({
            query: ({ fileId }) => ({
                url: `files/${fileId}`,
                params: {
                    apiKey: window.Kapowarr.apiKey,
                },
            }),

            transformResponse: (response: { result: RawFileData }) =>
                camelize(response.result),
        }),

        // PUT
        updateFile: build.mutation<void, UpdateFileParams>({
            query: ({ fileId, ...body }) => ({
                method: 'PUT',
                url: `files/${fileId}`,
                params: {
                    apiKey: window.Kapowarr.apiKey,
                },
                body: snakeify(body),
            }),
        }),

        // DELETE
        deleteFile: build.mutation<void, { fileId: number }>({
            query: ({ fileId }) => ({
                method: 'DELETE',
                url: `files/${fileId}`,
                params: {
                    apiKey: window.Kapowarr.apiKey,
                },
            }),
        }),
    }),
});

export const { useDeleteFileMutation, useGetFileQuery, useUpdateFileMutation } =
    extendedApi;
