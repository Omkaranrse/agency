'use client';

import * as React from 'react';
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock,
  XCircle,
  Ban,
  ArrowUpDown,
  FolderGit2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getRoleIcon } from './employee-roster';
import type { AgentRole, TaskRecord, TaskStatus } from '@/features/office/types';

export interface TasksOverviewTableProps {
  tasks: TaskRecord[];
  onSelectRole: (role: AgentRole) => void;
}

export function getTaskStatusBadge(status: TaskStatus) {
  switch (status) {
    case 'in_progress':
      return {
        label: 'In Progress',
        icon: Activity,
        classes: 'bg-accent/10 border-accent/30 text-accent dark:text-[#6CB3A8]',
      };
    case 'waiting_approval':
      return {
        label: 'Awaiting Approval',
        icon: AlertCircle,
        classes: 'bg-warning-surface border-warning/40 text-warning dark:text-[#E29D86]',
      };
    case 'completed':
      return {
        label: 'Completed',
        icon: CheckCircle2,
        classes: 'bg-success-surface border-success/30 text-success dark:text-[#72B889]',
      };
    case 'failed':
      return {
        label: 'Failed',
        icon: XCircle,
        classes: 'bg-danger-surface border-danger/40 text-danger dark:text-[#CF7982]',
      };
    case 'blocked':
      return {
        label: 'Blocked',
        icon: Ban,
        classes: 'bg-danger-surface border-danger/40 text-danger dark:text-[#CF7982]',
      };
    case 'pending':
    default:
      return {
        label: 'Pending',
        icon: Clock,
        classes: 'bg-surface-raised border-border text-muted-foreground',
      };
  }
}

export function TasksOverviewTable({ tasks, onSelectRole }: TasksOverviewTableProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">
            Delivery Tasks (Accessible View)
          </h3>
          <p className="text-xs text-muted-foreground">
            Tabular record of assigned agent tasks, execution timestamps, blockers, and artifacts.
          </p>
        </div>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-surface-raised border border-border text-muted-foreground">
          {tasks.length} tasks recorded
        </span>
      </div>

      <div className="rounded-lg border border-border bg-surface overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-surface-raised border-b border-border text-muted-foreground font-semibold uppercase text-[10px] tracking-wider select-none">
              <tr>
                <th scope="col" className="px-4 py-3">
                  Task Title
                </th>
                <th scope="col" className="px-4 py-3">
                  Assigned Agent
                </th>
                <th scope="col" className="px-4 py-3">
                  Status
                </th>
                <th scope="col" className="px-4 py-3">
                  Started
                </th>
                <th scope="col" className="px-4 py-3">
                  Completed
                </th>
                <th scope="col" className="px-4 py-3">
                  Activity / Blocker
                </th>
                <th scope="col" className="px-4 py-3">
                  Artifacts
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {tasks.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-4 py-8 text-center text-muted-foreground"
                  >
                    No tasks recorded for this run.
                  </td>
                </tr>
              ) : (
                tasks.map((task) => {
                  const RoleIcon = getRoleIcon(task.agent_role);
                  const badge = getTaskStatusBadge(task.status);
                  const BadgeIcon = badge.icon;

                  return (
                    <tr
                      key={task.id}
                      className="hover:bg-surface-raised/40 transition-colors"
                    >
                      {/* Title & Type */}
                      <td className="px-4 py-3 font-medium text-foreground">
                        <div>{task.title}</div>
                        <div className="text-[10px] text-muted-foreground font-mono">
                          {task.task_type}
                          {task.attempt_number > 1 && ` • Rev #${task.attempt_number}`}
                        </div>
                      </td>

                      {/* Role */}
                      <td className="px-4 py-3">
                        <button
                          type="button"
                          onClick={() => onSelectRole(task.agent_role)}
                          className="inline-flex items-center gap-1.5 font-medium text-foreground hover:text-accent focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring rounded"
                        >
                          <RoleIcon className="h-3.5 w-3.5 text-muted-foreground" />
                          <span className="capitalize">{task.agent_role}</span>
                        </button>
                      </td>

                      {/* Status */}
                      <td className="px-4 py-3">
                        <span
                          className={cn(
                            'inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium border select-none',
                            badge.classes
                          )}
                        >
                          <BadgeIcon className="h-2.5 w-2.5" />
                          <span>{badge.label}</span>
                        </span>
                      </td>

                      {/* Started */}
                      <td className="px-4 py-3 text-muted-foreground font-mono text-[11px]">
                        {task.started_at
                          ? new Date(task.started_at).toLocaleTimeString()
                          : '—'}
                      </td>

                      {/* Completed */}
                      <td className="px-4 py-3 text-muted-foreground font-mono text-[11px]">
                        {task.completed_at
                          ? new Date(task.completed_at).toLocaleTimeString()
                          : '—'}
                      </td>

                      {/* Blocker or Progress */}
                      <td className="px-4 py-3 max-w-xs">
                        {task.blocker ? (
                          <span className="text-danger font-mono text-[11px] line-clamp-2">
                            {task.blocker}
                          </span>
                        ) : task.progress_details ? (
                          <span className="text-muted-foreground text-[11px] line-clamp-2">
                            {task.progress_details}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>

                      {/* Artifacts */}
                      <td className="px-4 py-3">
                        {task.related_artifact_ids.length > 0 ? (
                          <div className="flex items-center gap-1 text-[11px] font-mono text-muted-foreground">
                            <FolderGit2 className="h-3 w-3 shrink-0" />
                            <span>{task.related_artifact_ids.length} files</span>
                          </div>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
