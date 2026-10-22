/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Payload to authorize production build and deployment for the current preview.
 */
export type ApproveRunRequest = {
    approver?: string;
    idempotency_key?: (string | null);
    /**
     * Preview revision being approved
     */
    revision: number;
};
