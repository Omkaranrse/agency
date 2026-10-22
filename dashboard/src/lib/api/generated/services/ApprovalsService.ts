/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApproveRunRequest } from '../models/ApproveRunRequest';
import type { ApproveRunResponse } from '../models/ApproveRunResponse';
import type { CancelRunRequest } from '../models/CancelRunRequest';
import type { CancelRunResponse } from '../models/CancelRunResponse';
import type { ReviseRunRequest } from '../models/ReviseRunRequest';
import type { ReviseRunResponse } from '../models/ReviseRunResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ApprovalsService {
    /**
     * Approve Run
     * Submit explicit human approval to resume compilation and deployment.
     * @param runId
     * @param requestBody
     * @returns ApproveRunResponse Successful Response
     * @throws ApiError
     */
    public static approveRunApiV1RunsRunIdApprovePost(
        runId: string,
        requestBody: ApproveRunRequest,
    ): CancelablePromise<ApproveRunResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/runs/{run_id}/approve',
            path: {
                'run_id': runId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Cancel Run
     * Request immediate cancellation of an active workflow.
     * @param runId
     * @param requestBody
     * @returns CancelRunResponse Successful Response
     * @throws ApiError
     */
    public static cancelRunApiV1RunsRunIdCancelPost(
        runId: string,
        requestBody: CancelRunRequest,
    ): CancelablePromise<CancelRunResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/runs/{run_id}/cancel',
            path: {
                'run_id': runId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Revise Run
     * Reject current prototype and request design/copy revisions.
     * @param runId
     * @param requestBody
     * @returns ReviseRunResponse Successful Response
     * @throws ApiError
     */
    public static reviseRunApiV1RunsRunIdRevisePost(
        runId: string,
        requestBody: ReviseRunRequest,
    ): CancelablePromise<ReviseRunResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/runs/{run_id}/revise',
            path: {
                'run_id': runId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
