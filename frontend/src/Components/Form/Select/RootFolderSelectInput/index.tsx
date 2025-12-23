// IMPORTS

// React
import { useMemo } from 'react';

// Redux
import { useGetRootFoldersQuery } from 'Store/Api/RootFolders';

// Specific Components
import RootFolderSelectInputOption from '../RootFolderSelectInputOption';
import RootFolderSelectInputSelectedValue from '../RootFolderSelectInputSelectedValue';

import EnhancedSelectInput, {
    type EnhancedSelectInputProps,
    type EnhancedSelectInputValue,
} from '../EnhancedSelectInput';

// Types
export interface RootFolderSelectInputValue extends EnhancedSelectInputValue<string> {
    freeSpace?: number;
}

export type RootFolderSelectInputProps<K extends string> = Omit<
    EnhancedSelectInputProps<K, EnhancedSelectInputValue<string>, string>,
    'values'
>;

// IMPLEMENTATIONS

export default function RootFolderSelectInput<K extends string>({
    name,
    onChange,
    value,
    ...otherProps
}: RootFolderSelectInputProps<K>) {
    const { data = [] } = useGetRootFoldersQuery();

    const values = useMemo(() => {
        return data.map(
            (f) =>
                ({
                    key: f.folder,
                    value: f.folder,
                    freeSpace: f.size.free,
                }) satisfies RootFolderSelectInputValue,
        );
    }, [data]);

    return (
        <>
            <EnhancedSelectInput
                {...otherProps}
                name={name}
                value={value}
                values={values}
                selectedValueComponent={RootFolderSelectInputSelectedValue}
                optionComponent={RootFolderSelectInputOption}
                onChange={onChange}
            />
        </>
    );
}
