import type {
  RunResponse,
  CreateRunRequest,
  CreateRunResponse,
  ListRunsResponse,
  BriefDTO,
  ArtifactMetadataDTO,
  ListArtifactsResponse,
  ApproveRunRequest,
  ApproveRunResponse,
  ReviseRunRequest,
  ReviseRunResponse,
  CancelRunRequest,
  CancelRunResponse,
} from '@/lib/api/generated';
import { RunState } from '@/lib/api/generated';

export { RunState };
export type {
  RunResponse,
  CreateRunRequest,
  CreateRunResponse,
  ListRunsResponse,
  BriefDTO,
  ArtifactMetadataDTO,
  ListArtifactsResponse,
  ApproveRunRequest,
  ApproveRunResponse,
  ReviseRunRequest,
  ReviseRunResponse,
  CancelRunRequest,
  CancelRunResponse,
};

export interface DomainEventEnvelope {
  event_id: string;
  run_id: string;
  event_type: string;
  occurred_at: string;
  payload: Record<string, any>;
}

export type EventStreamStatus =
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'disconnected'
  | 'error';

export interface RunsFilterState {
  status?: RunState;
  search?: string;
  page: number;
  pageSize: number;
}
