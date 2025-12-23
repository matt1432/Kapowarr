import type { IndexFilter } from 'Volume/Index';
import type { VolumePublicInfo } from 'Volume/Volume';

export default function getFilteredVolumeIDs(
    items: VolumePublicInfo[],
    filterKey: IndexFilter,
) {
    switch (filterKey) {
        case 'monitored':
            return items.filter((item) => item.monitored);

        case 'unmonitored':
            return items.filter((item) => !item.monitored);

        // TODO: improve logic for continuing and ended
        case 'continuing':
            return items.filter(({ marvelIssueCount, issueCount }) =>
                Boolean(
                    marvelIssueCount === 0 ? 0 : marvelIssueCount - issueCount,
                ),
            );

        case 'ended':
            return items.filter(
                ({ marvelIssueCount, issueCount }) =>
                    !(marvelIssueCount === 0
                        ? 0
                        : marvelIssueCount - issueCount),
            );

        case 'wanted':
            return items.filter(
                (item) =>
                    item.issuesDownloadedMonitored < item.issueCountMonitored,
            );

        default:
            return items;
    }
}
