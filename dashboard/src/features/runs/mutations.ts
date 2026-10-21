import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  createRun,
  approveRun,
  reviseRun,
  cancelRun,
} from './api';
import { runsKeys } from './queries';
import type {
  CreateRunRequest,
  CreateRunResponse,
  ApproveRunRequest,
  ApproveRunResponse,
  ReviseRunRequest,
  ReviseRunResponse,
  CancelRunRequest,
  CancelRunResponse,
} from './types';

export function useCreateRun() {
  const queryClient = useQueryClient();

  return useMutation<CreateRunResponse, Error, CreateRunRequest>({
    mutationFn: (data: CreateRunRequest) => createRun(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: runsKeys.lists() });
    },
  });
}

export function useApproveRun(runId: string) {
  const queryClient = useQueryClient();

  return useMutation<ApproveRunResponse, Error, ApproveRunRequest>({
    mutationFn: (data: ApproveRunRequest) => approveRun(runId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: runsKeys.detail(runId) });
      queryClient.invalidateQueries({ queryKey: runsKeys.lists() });
    },
  });
}

export function useReviseRun(runId: string) {
  const queryClient = useQueryClient();

  return useMutation<ReviseRunResponse, Error, ReviseRunRequest>({
    mutationFn: (data: ReviseRunRequest) => reviseRun(runId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: runsKeys.detail(runId) });
      queryClient.invalidateQueries({ queryKey: runsKeys.lists() });
    },
  });
}

export function useCancelRun(runId: string) {
  const queryClient = useQueryClient();

  return useMutation<CancelRunResponse, Error, CancelRunRequest>({
    mutationFn: (data: CancelRunRequest) => cancelRun(runId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: runsKeys.detail(runId) });
      queryClient.invalidateQueries({ queryKey: runsKeys.lists() });
    },
  });
}
