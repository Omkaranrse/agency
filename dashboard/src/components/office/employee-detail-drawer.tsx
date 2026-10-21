'use client';

import * as React from 'react';
import Link from 'next/link';
import {
  X,
  Clock,
  Activity,
  AlertTriangle,
  FolderGit2,
  ExternalLink,
  Shield,
  CheckCircle2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getRoleIcon, getEmployeeStatusBadge } from './employee-roster';
import { AIManagerAvatar } from '@/components/manager/ai-manager-avatar';
import type { OfficeEmployeeState, TaskRecord } from '@/features/office/types';

export interface EmployeeDetailDrawerProps {
  employee: OfficeEmployeeState | null;
  task: TaskRecord | null;
  runId: string;
  onClose: () => void;
}

export function EmployeeDetailDrawer({
  employee,
  task,
  runId,
  onClose,
}: EmployeeDetailDrawerProps) {
  if (!employee) return null;

  const RoleIcon = getRoleIcon(employee.role);
  const statusBadge = getEmployeeStatusBadge(employee.status);
  const StatusIcon = statusBadge.icon;

  return (
    <div
      className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-surface border-l border-border shadow-2xl flex flex-col transition-transform animate-in slide-in-from-right duration-200"
      role="dialog"
      aria-modal="true"
      aria-label={`${employee.name} details`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border">
        <div className="flex items-center gap-3">
          {employee.role === 'manager' ? (
            <AIManagerAvatar size="md" showBadge={false} />
          ) : (
            <div className="flex h-9 w-9 items-center justify-center rounded-md bg-accent text-accent-foreground">
              <RoleIcon className="h-5 w-5" aria-hidden="true" />
            </div>
          )}
          <div>
            <h2 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
              <span>{employee.name}</span>
              {employee.role === 'manager' && (
                <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-accent/15 text-accent border border-accent/25">
                  MASCOT
                </span>
              )}
            </h2>
            <p className="text-xs text-muted-foreground">{employee.title}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-label="Close detail panel"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Body Content */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5 text-xs">
        {/* Status Section */}
        <div className="p-3 rounded-lg border border-border bg-surface-raised/40 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground font-medium text-[11px]">Current Status</span>
            <span
              className={cn(
                'inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium border select-none',
                statusBadge.classes
              )}
            >
              <StatusIcon className="h-3 w-3 shrink-0" aria-hidden="true" />
              <span>{statusBadge.label}</span>
            </span>
          </div>

          <div className="flex items-center justify-between text-[11px]">
            <span className="text-muted-foreground">Assigned Workstation</span>
            <span className="font-mono text-foreground uppercase tracking-tight">
              {employee.workstation.replace('_', ' ')}
            </span>
          </div>

          <div className="flex items-center justify-between text-[11px]">
            <span className="text-muted-foreground">Role Execution Type</span>
            <span className="inline-flex items-center gap-1 text-foreground">
              <Shield className="h-3 w-3 text-accent" />
              {employee.is_logical_role ? 'Human Gate / Operator' : 'Autonomous AI Agent'}
            </span>
          </div>
        </div>

        {/* Current Activity / Progress */}
        <div className="space-y-1.5">
          <h4 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Current Activity
          </h4>
          <div className="p-3 rounded-lg border border-border bg-surface text-foreground font-mono text-[11px] leading-relaxed">
            {employee.current_activity || 'Awaiting incoming workflow milestone task.'}
          </div>
        </div>

        {/* Active Task Details */}
        {task && (
          <div className="space-y-3">
            <h4 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Assigned Task
            </h4>
            <div className="p-3.5 rounded-lg border border-border bg-surface space-y-2.5">
              <div className="font-medium text-xs text-foreground">{task.title}</div>

              {task.progress_details && (
                <div className="text-[11px] text-muted-foreground bg-surface-raised p-2 rounded">
                  {task.progress_details}
                </div>
              )}

              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-border/80 text-[11px]">
                <div>
                  <span className="text-muted-foreground block">Started At</span>
                  <span className="font-mono text-foreground">
                    {task.started_at
                      ? new Date(task.started_at).toLocaleTimeString()
                      : 'Pending'}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground block">Completed At</span>
                  <span className="font-mono text-foreground">
                    {task.completed_at
                      ? new Date(task.completed_at).toLocaleTimeString()
                      : 'In Progress'}
                  </span>
                </div>
              </div>

              {task.attempt_number > 1 && (
                <div className="text-[11px] text-muted-foreground flex items-center justify-between">
                  <span>Revision Cycle / Attempt</span>
                  <span className="font-mono font-medium text-foreground">
                    #{task.attempt_number}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Blockers & Error Details */}
        {task?.blocker && (
          <div className="space-y-1.5">
            <h4 className="text-[11px] font-semibold uppercase tracking-wider text-danger flex items-center gap-1.5">
              <AlertTriangle className="h-3.5 w-3.5" />
              Active Blocker
            </h4>
            <div className="p-3 rounded-lg border border-danger/40 bg-danger-surface text-danger text-[11px] leading-relaxed font-mono">
              {task.blocker}
            </div>
          </div>
        )}

        {/* Completed Steps */}
        <div className="space-y-1.5">
          <h4 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Progress Metrics
          </h4>
          <div className="flex items-center justify-between p-3 rounded-lg border border-border bg-surface">
            <span className="text-muted-foreground flex items-center gap-1.5">
              <CheckCircle2 className="h-3.5 w-3.5 text-success" />
              Completed Milestones
            </span>
            <span className="font-mono font-semibold text-foreground">
              {employee.completed_steps_count}
            </span>
          </div>
        </div>

        {/* Related Artifacts */}
        {task && task.related_artifact_ids.length > 0 && (
          <div className="space-y-1.5">
            <h4 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Produced Artifacts
            </h4>
            <ul className="space-y-1">
              {task.related_artifact_ids.map((artId) => (
                <li
                  key={artId}
                  className="flex items-center gap-2 p-2 rounded border border-border bg-surface font-mono text-[10px] text-foreground"
                >
                  <FolderGit2 className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                  <span className="truncate">{artId}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Technical IDs */}
        <div className="pt-3 border-t border-border space-y-1 text-[10px] text-muted-foreground font-mono">
          <div className="truncate">Run ID: {runId}</div>
          {task && <div className="truncate">Task ID: {task.id}</div>}
        </div>
      </div>

      {/* Footer Navigation */}
      <div className="p-4 border-t border-border bg-surface-raised flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Link
            href={`/runs/${encodeURIComponent(runId)}`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-border text-xs font-medium text-foreground hover:bg-surface transition-colors"
          >
            <span>Run Details</span>
            <ExternalLink className="h-3.5 w-3.5" />
          </Link>

          {employee.role === 'manager' && (
            <Link
              href="/manager"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-accent/30 bg-accent/10 text-xs font-semibold text-accent hover:bg-accent/20 transition-colors"
            >
              <AIManagerAvatar size="xs" showBadge={false} />
              <span>Talk to Alex</span>
            </Link>
          )}
        </div>

        <button
          type="button"
          onClick={onClose}
          className="px-3 py-1.5 rounded bg-foreground text-background text-xs font-medium hover:opacity-90 transition-opacity"
        >
          Close
        </button>
      </div>
    </div>
  );
}
