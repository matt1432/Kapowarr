const dateTypes = {
    COVER_DATE: 'cover_date',
    STORE_DATE: 'store_date',
} as const;

export default dateTypes;

export type DateType = (typeof dateTypes)[keyof typeof dateTypes];
