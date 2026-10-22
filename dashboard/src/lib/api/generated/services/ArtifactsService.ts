/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ListArtifactsResponse } from '../models/ListArtifactsResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ArtifactsService {
    /**
     * List Run Artifacts
     * List metadata for all approved artifacts produced by a run.
     * @param runId
     * @returns ListArtifactsResponse Successful Response
     * @throws ApiError
     */
    public static listRunArtifactsApiV1RunsRunIdArtifactsGet(
        runId: string,
    ): CancelablePromise<ListArtifactsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/runs/{run_id}/artifacts',
            path: {
                'run_id': runId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Run Artifact
     * Download an approved artifact with safe headers and isolated content disposition.
     * @param runId
     * @param artifactId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getRunArtifactApiV1RunsRunIdArtifactsArtifactIdGet(
        runId: string,
        artifactId: string,
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/runs/{run_id}/artifacts/{artifact_id}',
            path: {
                'run_id': runId,
                'artifact_id': artifactId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
