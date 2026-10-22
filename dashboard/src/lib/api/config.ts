import { OpenAPI } from './generated/core/OpenAPI';
import { ApiError } from './generated/core/ApiError';

/**
 * Configure API client defaults.
 */
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function configureApiClient() {
  OpenAPI.BASE = API_BASE_URL;

  // Support operator key configuration for trusted environments
  OpenAPI.HEADERS = async () => {
    const headers: Record<string, string> = {
      'Accept': 'application/json',
    };

    if (typeof window !== 'undefined') {
      try {
        const storedKey = localStorage.getItem('agency-api-key');
        if (storedKey) {
          headers['X-API-Key'] = storedKey;
        }
      } catch {
        // localStorage not available
      }
    }

    return headers;
  };
}

// Automatically configure once on module evaluation
configureApiClient();

export interface ParsedApiError {
  message: string;
  code?: string;
  status: number;
  validationErrors?: Record<string, string[]>;
}

/**
 * Extracts a user-safe, plain-language error message and diagnostic metadata
 * from an API error or unexpected exception without exposing internal stack traces.
 */
export function parseApiError(error: unknown): ParsedApiError {
  if (error instanceof ApiError) {
    const status = error.status;
    const body = error.body;

    if (body) {
      // 1. Structured FastAPI detail object: { code: string, message: string }
      if (typeof body.detail === 'object' && body.detail !== null && !Array.isArray(body.detail)) {
        return {
          status,
          message: body.detail.message || error.message || 'Operation failed',
          code: body.detail.code,
        };
      }

      // 2. Simple string detail: { detail: string }
      if (typeof body.detail === 'string') {
        return {
          status,
          message: body.detail,
        };
      }

      // 3. Validation error list: { detail: Array<{ loc: string[], msg: string, type: string }> }
      if (Array.isArray(body.detail)) {
        const validationErrors: Record<string, string[]> = {};
        for (const item of body.detail) {
          const field = Array.isArray(item.loc) ? item.loc.slice(-1)[0] : 'field';
          if (!validationErrors[field]) {
            validationErrors[field] = [];
          }
          validationErrors[field].push(item.msg || 'Invalid input');
        }

        return {
          status,
          message: 'The submitted request contained invalid or incomplete parameters.',
          validationErrors,
        };
      }
    }

    if (status === 401) {
      return { status, message: 'Authentication required. Please verify your operator credentials.' };
    }
    if (status === 403) {
      return { status, message: 'You do not have permission to perform this operation.' };
    }
    if (status === 404) {
      return { status, message: 'The requested run or resource could not be found.' };
    }
    if (status === 409) {
      return { status, message: 'Conflict: The run state or approval revision has changed. Please refresh and review.' };
    }
    if (status === 429) {
      return { status, message: 'Too many requests. Please wait a moment before trying again.' };
    }

    return {
      status,
      message: error.message || `Request failed with status ${status}`,
    };
  }

  if (error instanceof Error) {
    return {
      status: 0,
      message: error.message || 'A network error occurred. Please check your connection.',
    };
  }

  return {
    status: 0,
    message: 'An unexpected error occurred.',
  };
}
