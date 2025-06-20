import { type Field } from './Field';

export interface ValidationFailure {
    isWarning: boolean;
    propertyName: string;
    errorMessage: string;
    infoLink?: string;
    detailedDescription?: string;
    severity: 'error' | 'warning';
}

export interface ValidationError extends ValidationFailure {
    isWarning: false;
}

export interface ValidationWarning extends ValidationFailure {
    isWarning: true;
}

export interface Failure {
    errorMessage: ValidationFailure['errorMessage'];
    infoLink: ValidationFailure['infoLink'];
    detailedDescription: ValidationFailure['detailedDescription'];
}

export interface Pending<T> {
    value: T;
    errors: Failure[];
    warnings: Failure[];
    pending: boolean;
    previousValue?: T;
}

export interface PendingField<T> extends Field, Omit<Pending<T>, 'previousValue' | 'value'> {
    previousValue?: Field['value'];
}

type Mapped<T> = {
    [Prop in keyof T]: {
        value: T[Prop];
        errors: Failure[];
        warnings: Failure[];
        pending?: boolean;
        previousValue?: T[Prop];
    };
};

export type PendingSection<T> = Mapped<T> & {
    implementationName?: string;
    fields?: PendingField<T>[];
};
