import type { CamelCasedProperties } from 'type-fest';

export interface RawFileData {
    id: number;
    filepath: string;
    size: number;
    releaser: string;
    scan_type: string;
    resolution: string;
    dpi: string;
    notes: string;
}

export type FileData = CamelCasedProperties<RawFileData>;

export interface RawGeneralFileData extends RawFileData {
    file_type: string;
}

export type GeneralFileData = CamelCasedProperties<RawGeneralFileData>;

export interface RawIssueFileData extends RawFileData {
    series: string;
    year?: number;
    volume_number?: number | [number, number];
    special_version?: string;
    issue_number?: number | [number, number];
    annual: boolean;
    is_metadata_file: boolean;
    is_image_file: boolean;
}

export type IssueFileData = CamelCasedProperties<RawIssueFileData>;

export interface RawIssueData {
    id: number;
    volume_id: number;
    comicvine_id: number;
    issue_number: string;
    calculated_issue_number: number;
    title: string | null;
    date: string | null;
    description: string | null;
    monitored: boolean;
    files: RawIssueFileData[];
}

export type IssueData = Omit<CamelCasedProperties<RawIssueData>, 'files'> & {
    files: IssueFileData[];
};

export type RawIssue = RawIssueData;

export type Issue = IssueData;
