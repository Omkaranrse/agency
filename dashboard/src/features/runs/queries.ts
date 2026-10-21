import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { fetchRuns, fetchRun, fetchArtifacts, type ListRunsParams } from './api';
import type { ListRunsResponse, RunResponse, ListArtifactsResponse } from './types';

export const runsKeys = {
  all: ['runs'] as const,
  lists: () => [...runsKeys.all, 'list'] as const,
  list: (params: ListRunsParams) => [...runsKeys.lists(), params] as const,
  details: () => [...runsKeys.all, 'detail'] as const,
  detail: (runId: string) => [...runsKeys.details(), runId] as const,
  artifacts: (runId: string) => [...runsKeys.detail(runId), 'artifacts'] as const,
};

export function useRunsList(params: ListRunsParams = {}) {
  return useQuery<ListRunsResponse, Error>({
    queryKey: runsKeys.list(params),
    queryFn: () => fetchRuns(params),
    placeholderData: keepPreviousData,
  });
}

export function useRunDetails(runId: string | undefined) {
  return useQuery<RunResponse, Error>({
    queryKey: runsKeys.detail(runId ?? ''),
    queryFn: () => {
      if (!runId) throw new Error('Run ID is required');
      return fetchRun(runId);
    },
    enabled: Boolean(runId),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;
      const status = data.status.toUpperCase();
      // Poll active runs periodically as secondary reconciliation to SSE
      const isActive = [
        'CREATED',
        'PLANNING',
        'PROTOTYPING',
        'BUILDING',
        'TESTING',
        'DEPLOYING',
      ].includes(status);
      return isActive ? 8000 : false;
    },
  });
}

export function useRunArtifacts(runId: string | undefined) {
  return useQuery<ListArtifactsResponse, Error>({
    queryKey: runsKeys.artifacts(runId ?? ''),
    queryFn: () => {
      if (!runId) throw new Error('Run ID is required');
      return fetchArtifacts(runId);
    },
    enabled: Boolean(runId),
  });
}
