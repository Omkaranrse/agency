/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class EventsService {
    /**
     * Stream Run Events
     * Stream real-time and replayed domain events for a run via Server-Sent Events.
     * @param runId
     * @param lastEventId
     * @returns any Successful Response
     * @throws ApiError
     */
    public static streamRunEventsApiV1RunsRunIdEventsGet(
        runId: string,
        lastEventId?: (string | null),
    ): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/runs/{run_id}/events',
            path: {
                'run_id': runId,
            },
            headers: {
                'Last-Event-ID': lastEventId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
