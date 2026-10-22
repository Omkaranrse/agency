/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BriefDTO } from './BriefDTO';
/**
 * Payload to initiate a new website delivery run.
 */
export type CreateRunRequest = {
    brief: BriefDTO;
    idempotency_key?: (string | null);
    project_id?: (string | null);
    template_variant?: (string | null);
};
