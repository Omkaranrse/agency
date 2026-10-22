/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PaginationMeta } from './PaginationMeta';
import type { RunResponse } from './RunResponse';
/**
 * Paginated collection of Run summaries.
 */
export type ListRunsResponse = {
    items: Array<RunResponse>;
    pagination: PaginationMeta;
};
