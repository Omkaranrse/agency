/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Pagination metadata for paginated collection responses.
 */
export type PaginationMeta = {
    /**
     * True if more pages exist
     */
    has_next: boolean;
    /**
     * Page limit applied to query
     */
    limit: number;
    /**
     * Offset applied to query
     */
    offset: number;
    /**
     * Total number of items available
     */
    total: number;
};
