export type AgentRole =
  | 'manager'
  | 'pm'
  | 'designer'
  | 'builder'
  | 'qa'
  | 'reviewer'
  | 'devops';

export type WorkstationId =
  | 'manager_desk'
  | 'planning_desk'
  | 'design_station'
  | 'development_station'
  | 'qa_station'
  | 'review_area'
  | 'operations_station';

export type EmployeeStatus =
  | 'idle'
  | 'walking'
  | 'working'
  | 'waiting_approval'
  | 'blocked'
  | 'reviewing'
  | 'completed'
  | 'failed';

export type TaskStatus =
  | 'pending'
  | 'in_progress'
  | 'waiting_approval'
  | 'completed'
  | 'failed'
  | 'blocked';

export interface TaskRecord {
  id: string;
  run_id: string;
  agent_role: AgentRole;
  task_type: string;
  title: string;
  status: TaskStatus;
  started_at: string | null;
  updated_at: string | null;
  completed_at: string | null;
  progress_details: string | null;
  blocker: string | null;
  attempt_number: number;
  related_artifact_ids: string[];
}

export interface OfficeEmployeeState {
  role: AgentRole;
  name: string;
  title: string;
  avatar: string;
  workstation: WorkstationId;
  status: EmployeeStatus;
  active_task_id: string | null;
  current_activity: string | null;
  last_active_at: string | null;
  is_logical_role: boolean;
  completed_steps_count: number;
}

export interface WorkstationState {
  id: WorkstationId;
  name: string;
  description: string;
  assigned_role: AgentRole;
  active_task_id: string | null;
  queued_task_ids: string[];
  status: string;
}

export interface OfficeState {
  run_id: string;
  project_id: string;
  run_status: string;
  current_stage: string;
  employees: OfficeEmployeeState[];
  workstations: WorkstationState[];
  tasks: TaskRecord[];
  active_task_id: string | null;
  blockers: string[];
  updated_at: string;
}

export interface ListTasksResponse {
  items: TaskRecord[];
  total: number;
}
