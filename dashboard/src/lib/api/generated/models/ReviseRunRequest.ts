/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Payload to reject current preview and request targeted modifications.
 */
export type ReviseRunRequest = {
    /**
     * Mandatory actionable feedback for revision
     */
    comment: string;
    idempotency_key?: (string | null);
    /**
     * Current preview revision to revise
     */
    revision: number;
};
