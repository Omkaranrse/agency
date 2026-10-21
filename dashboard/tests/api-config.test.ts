import { describe, it, expect } from 'vitest';
import { parseApiError } from '@/lib/api/config';
import { ApiError } from '@/lib/api/generated/core/ApiError';

describe('API Error Parser and Safe Messages', () => {
  it('parses structured detail object with code and message', () => {
    const error = new ApiError(
      {} as any,
      {
        url: '/api/v1/runs/test/approve',
        status: 409,
        statusText: 'Conflict',
        body: {
          detail: {
            code: 'STALE_APPROVAL',
            message: 'Approval revision 1 is stale. Current preview revision is 2.',
          },
        },
        ok: false,
      },
      'Request failed'
    );

    const parsed = parseApiError(error);
    expect(parsed.status).toBe(409);
    expect(parsed.code).toBe('STALE_APPROVAL');
    expect(parsed.message).toBe('Approval revision 1 is stale. Current preview revision is 2.');
  });

  it('parses simple string detail message', () => {
    const error = new ApiError(
      {} as any,
      {
        url: '/api/v1/runs',
        status: 400,
        statusText: 'Bad Request',
        body: {
          detail: 'Run is not awaiting approval.',
        },
        ok: false,
      },
      'Request failed'
    );

    const parsed = parseApiError(error);
    expect(parsed.status).toBe(400);
    expect(parsed.message).toBe('Run is not awaiting approval.');
  });

  it('parses FastAPI 422 validation error arrays', () => {
    const error = new ApiError(
      {} as any,
      {
        url: '/api/v1/runs',
        status: 422,
        statusText: 'Unprocessable Entity',
        body: {
          detail: [
            { loc: ['body', 'brief', 'client_name'], msg: 'String should have at least 1 character', type: 'string_too_short' },
            { loc: ['body', 'brief', 'pages'], msg: 'List should have at least 1 item', type: 'too_short' },
          ],
        },
        ok: false,
      },
      'Validation Error'
    );

    const parsed = parseApiError(error);
    expect(parsed.status).toBe(422);
    expect(parsed.validationErrors).toBeDefined();
    expect(parsed.validationErrors?.client_name).toContain('String should have at least 1 character');
    expect(parsed.validationErrors?.pages).toContain('List should have at least 1 item');
  });

  it('returns safe fallback messages for 401, 403, 404, 429', () => {
    const e401 = new ApiError({} as any, { url: '', status: 401, statusText: 'Unauthorized', body: null, ok: false }, '');
    expect(parseApiError(e401).message).toContain('Authentication required');

    const e404 = new ApiError({} as any, { url: '', status: 404, statusText: 'Not Found', body: null, ok: false }, '');
    expect(parseApiError(e404).message).toContain('could not be found');

    const e409 = new ApiError({} as any, { url: '', status: 409, statusText: 'Conflict', body: null, ok: false }, '');
    expect(parseApiError(e409).message).toContain('Conflict');

    const e429 = new ApiError({} as any, { url: '', status: 429, statusText: 'Too Many Requests', body: null, ok: false }, '');
    expect(parseApiError(e429).message).toContain('Too many requests');
  });
});
