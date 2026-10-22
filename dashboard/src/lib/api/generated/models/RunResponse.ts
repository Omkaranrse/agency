/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Complete summary view of an agency Run aggregate.
 */
export type RunResponse = {
    approval_state?: (string | null);
    build_summary?: (Record<string, any> | null);
    created_at: string;
    current_revision?: number;
    current_stage: string;
    failure_details?: (Record<string, any> | null);
    preview_url?: (string | null);
    production_url?: (string | null);
    project_id: string;
    qa_summary?: (Record<string, any> | null);
    run_id: string;
    status: string;
    updated_at: string;
};
