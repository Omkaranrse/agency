import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { fetchOfficeState, fetchOfficeTasks } from './api';
import type { ListTasksResponse, OfficeState } from './types';

export const officeKeys = {
  all: ['office'] as const,
  state: (runId: string) => [...officeKeys.all, 'state', runId] as const,
  tasks: (runId: string) => [...officeKeys.all, 'tasks', runId] as const,
};

export function useOfficeState(runId: string | undefined) {
  return useQuery<OfficeState, Error>({
    queryKey: officeKeys.state(runId ?? ''),
    queryFn: () => {
      if (!runId) throw new Error('Run ID is required');
      return fetchOfficeState(runId);
    },
    enabled: Boolean(runId),
    placeholderData: keepPreviousData,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;
      const status = data.run_status.toUpperCase();
      // Keep office view synced for active runs
      const isActive = [
        'CREATED',
        'PLANNING',
        'PROTOTYPING',
        'BUILDING',
        'TESTING',
        'DEPLOYING',
      ].includes(status);
      return isActive ? 5000 : false;
    },
  });
}

export function useOfficeTasks(runId: string | undefined) {
  return useQuery<ListTasksResponse, Error>({
    queryKey: officeKeys.tasks(runId ?? ''),
    queryFn: () => {
      if (!runId) throw new Error('Run ID is required');
      return fetchOfficeTasks(runId);
    },
    enabled: Boolean(runId),
  });
}
