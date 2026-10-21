import { API_BASE_URL } from '@/lib/api/config';
import type { ListTasksResponse, OfficeState } from './types';

function getHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (typeof window !== 'undefined') {
    try {
      const apiKey = localStorage.getItem('agency-api-key');
      if (apiKey) {
        headers['X-API-Key'] = apiKey;
      }
    } catch {
      // Ignore localStorage availability errors
    }
  }
  return headers;
}

export async function fetchOfficeState(runId: string): Promise<OfficeState> {
  const url = `${API_BASE_URL}/api/v1/runs/${encodeURIComponent(runId)}/office-state`;
  const response = await fetch(url, {
    method: 'GET',
    headers: getHeaders(),
  });

  if (!response.ok) {
    let errorMsg = `Failed to fetch office state (${response.status})`;
    try {
      const data = await response.json();
      if (data?.detail?.message) errorMsg = data.detail.message;
      else if (typeof data?.detail === 'string') errorMsg = data.detail;
    } catch {
      // not JSON
    }
    throw new Error(errorMsg);
  }

  return response.json();
}

export async function fetchOfficeTasks(runId: string): Promise<ListTasksResponse> {
  const url = `${API_BASE_URL}/api/v1/runs/${encodeURIComponent(runId)}/tasks`;
  const response = await fetch(url, {
    method: 'GET',
    headers: getHeaders(),
  });

  if (!response.ok) {
    let errorMsg = `Failed to fetch office tasks (${response.status})`;
    try {
      const data = await response.json();
      if (data?.detail?.message) errorMsg = data.detail.message;
      else if (typeof data?.detail === 'string') errorMsg = data.detail;
    } catch {
      // not JSON
    }
    throw new Error(errorMsg);
  }

  return response.json();
}
