/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Result returned after revision request is accepted.
 */
export type ReviseRunResponse = {
    comment: string;
    decision?: string;
    new_revision: number;
    recorded_at?: string;
    run_id: string;
    status: string;
};
