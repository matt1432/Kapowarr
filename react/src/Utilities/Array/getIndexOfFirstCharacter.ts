import { type Volumes } from 'Volumes/Volumes';

const STARTS_WITH_NUMBER_REGEX = /^\d/;

export default function getIndexOfFirstCharacter(items: Volumes[], character: string) {
    return items.findIndex((item) => {
        const firstCharacter = item.sortTitle.charAt(0);

        if (character === '#') {
            return STARTS_WITH_NUMBER_REGEX.test(firstCharacter);
        }

        return firstCharacter === character;
    });
}
