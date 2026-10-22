/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CreateRunRequest } from '../models/CreateRunRequest';
import type { CreateRunResponse } from '../models/CreateRunResponse';
import type { ListRunsResponse } from '../models/ListRunsResponse';
import type { RunResponse } from '../models/RunResponse';
import type { RunState } from '../models/RunState';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class RunsService {
    /**
     * List Runs
     * Retrieve a paginated, deterministically sorted list of runs.
     * @param limit
     * @param offset
     * @param status
     * @returns ListRunsResponse Successful Response
     * @throws ApiError
     */
    public static listRunsApiV1RunsGet(
        limit: number = 50,
        offset?: number,
        status?: (RunState | null),
    ): CancelablePromise<ListRunsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/runs',
            query: {
                'limit': limit,
                'offset': offset,
                'status': status,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Run
     * Validate client brief, persist initial Run aggregate, and enqueue execution.
     * @param requestBody
     * @returns CreateRunResponse Successful Response
     * @throws ApiError
     */
    public static createRunApiV1RunsPost(
        requestBody: CreateRunRequest,
    ): CancelablePromise<CreateRunResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/runs',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Run
     * Retrieve detailed state and metadata for a specific run.
     * @param runId
     * @returns RunResponse Successful Response
     * @throws ApiError
     */
    public static getRunApiV1RunsRunIdGet(
        runId: string,
    ): CancelablePromise<RunResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/runs/{run_id}',
            path: {
                'run_id': runId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
