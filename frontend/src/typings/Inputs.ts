export type InputChanged<K extends string, T> = {
    name: K;
    value: T;
};

export interface CheckInputChanged<K extends string> extends InputChanged<
    K,
    boolean
> {
    shiftKey: boolean;
}

export interface FileInputChanged<K extends string> extends InputChanged<
    K,
    string
> {
    files: FileList | null | undefined;
}

export interface EnhancedSelectInputChanged<
    K extends string,
    T,
> extends InputChanged<K, T> {
    additionalProperties?: unknown;
}

export interface SelectStateInputProps {
    id: number | string;
    value: boolean | null;
    shiftKey: boolean;
}
