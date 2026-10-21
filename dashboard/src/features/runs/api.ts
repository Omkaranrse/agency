import {
  RunsService,
  ApprovalsService,
  ArtifactsService,
  type CreateRunRequest,
  type CreateRunResponse,
  type ListRunsResponse,
  type RunResponse,
  type RunState,
  type ApproveRunRequest,
  type ApproveRunResponse,
  type ReviseRunRequest,
  type ReviseRunResponse,
  type CancelRunRequest,
  type CancelRunResponse,
  type ListArtifactsResponse,
} from '@/lib/api/generated';
import { API_BASE_URL } from '@/lib/api/config';

export interface ListRunsParams {
  limit?: number;
  offset?: number;
  status?: RunState;
}

export async function fetchRuns(params: ListRunsParams = {}): Promise<ListRunsResponse> {
  return RunsService.listRunsApiV1RunsGet(
    params.limit ?? 50,
    params.offset ?? 0,
    params.status ?? undefined
  );
}

export async function fetchRun(runId: string): Promise<RunResponse> {
  return RunsService.getRunApiV1RunsRunIdGet(runId);
}

export async function createRun(request: CreateRunRequest): Promise<CreateRunResponse> {
  return RunsService.createRunApiV1RunsPost(request);
}

export async function approveRun(
  runId: string,
  request: ApproveRunRequest
): Promise<ApproveRunResponse> {
  return ApprovalsService.approveRunApiV1RunsRunIdApprovePost(runId, request);
}

export async function reviseRun(
  runId: string,
  request: ReviseRunRequest
): Promise<ReviseRunResponse> {
  return ApprovalsService.reviseRunApiV1RunsRunIdRevisePost(runId, request);
}

export async function cancelRun(
  runId: string,
  request: CancelRunRequest
): Promise<CancelRunResponse> {
  return ApprovalsService.cancelRunApiV1RunsRunIdCancelPost(runId, request);
}

export async function fetchArtifacts(runId: string): Promise<ListArtifactsResponse> {
  return ArtifactsService.listRunArtifactsApiV1RunsRunIdArtifactsGet(runId);
}

/**
 * Downloads a specific run artifact using authenticated fetch and triggers
 * an isolated browser attachment download with proper filename sanitation.
 */
export async function downloadArtifact(
  runId: string,
  artifactId: string,
  fallbackFilename: string = 'artifact.json'
): Promise<void> {
  const url = `${API_BASE_URL}/api/v1/runs/${encodeURIComponent(runId)}/artifacts/${encodeURIComponent(artifactId)}`;

  const headers: Record<string, string> = {};
  if (typeof window !== 'undefined') {
    try {
      const apiKey = localStorage.getItem('agency-api-key');
      if (apiKey) headers['X-API-Key'] = apiKey;
    } catch {
      // localStorage may fail
    }
  }

  const response = await fetch(url, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    let errorMsg = `Download failed with status ${response.status}`;
    try {
      const json = await response.json();
      if (json?.detail?.message) errorMsg = json.detail.message;
      else if (typeof json?.detail === 'string') errorMsg = json.detail;
    } catch {
      // not JSON
    }
    throw new Error(errorMsg);
  }

  // Parse filename from Content-Disposition if present
  let filename = fallbackFilename;
  const disposition = response.headers.get('Content-Disposition');
  if (disposition) {
    const filenameMatch = disposition.match(/filename=["']?([^"';]+)["']?/i);
    if (filenameMatch && filenameMatch[1]) {
      filename = filenameMatch[1].trim();
    }
  }

  const blob = await response.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = downloadUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  window.URL.revokeObjectURL(downloadUrl);
}
