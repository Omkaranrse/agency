/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Response returned when a run creation request is accepted.
 */
export type CreateRunResponse = {
    created_at?: string;
    current_stage: string;
    project_id: string;
    run_id: string;
    status: string;
};
