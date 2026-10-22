/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * The explicit states representing a Run lifecycle in the state machine.
 */
export enum RunState {
    CREATED = 'CREATED',
    PLANNING = 'PLANNING',
    PROTOTYPING = 'PROTOTYPING',
    AWAITING_APPROVAL = 'AWAITING_APPROVAL',
    BUILDING = 'BUILDING',
    TESTING = 'TESTING',
    DEPLOYING = 'DEPLOYING',
    COMPLETED = 'COMPLETED',
    FAILED = 'FAILED',
    CANCELLED = 'CANCELLED',
}
