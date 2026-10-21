'use client';

import * as React from 'react';
import {
  Layers,
  Activity,
  CheckCircle2,
  AlertCircle,
  XCircle,
  Ban,
  Clock,
  ArrowRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { getRoleIcon } from './employee-roster';
import type { AgentRole, WorkstationState, TaskRecord } from '@/features/office/types';

export interface WorkstationsPanelProps {
  workstations: WorkstationState[];
  tasks: TaskRecord[];
  onSelectRole: (role: AgentRole) => void;
}

export function getStationBadge(status: string) {
  switch (status) {
    case 'active':
      return {
        label: 'Active Station',
        icon: Activity,
        classes: 'bg-accent/10 border-accent/30 text-accent dark:text-[#6CB3A8]',
      };
    case 'waiting_approval':
      return {
        label: 'Awaiting Sign-off',
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
    case 'idle':
    default:
      return {
        label: 'Idle Standby',
        icon: Clock,
        classes: 'bg-surface-raised border-border text-muted-foreground',
      };
  }
}

export function WorkstationsPanel({
  workstations,
  tasks,
  onSelectRole,
}: WorkstationsPanelProps) {
  const taskById = React.useMemo(() => {
    return new Map(tasks.map((t) => [t.id, t]));
  }, [tasks]);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Agency Workstations</h3>
          <p className="text-xs text-muted-foreground">
            Workflow execution zones across architecture, synthesis, verification, and deployment.
          </p>
        </div>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-surface-raised border border-border text-muted-foreground">
          {workstations.length} zones
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3.5">
        {workstations.map((station) => {
          const badge = getStationBadge(station.status);
          const BadgeIcon = badge.icon;
          const RoleIcon = getRoleIcon(station.assigned_role);
          const activeTask = station.active_task_id
            ? taskById.get(station.active_task_id)
            : null;

          return (
            <div
              key={station.id}
              className={cn(
                'flex flex-col justify-between p-4 rounded-lg border bg-surface transition-all',
                station.status === 'active'
                  ? 'border-accent/60 bg-accent/5 dark:bg-accent/10 shadow-sm'
                  : station.status === 'waiting_approval'
                  ? 'border-warning/50 bg-warning-surface/30'
                  : 'border-border'
              )}
            >
              <div>
                {/* Station header */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className="flex h-7 w-7 items-center justify-center rounded bg-surface-raised border border-border text-foreground">
                      <RoleIcon className="h-4 w-4" />
                    </div>
                    <div>
                      <h4 className="text-xs font-semibold text-foreground">{station.name}</h4>
                      <p className="text-[10px] text-muted-foreground capitalize">
                        {station.assigned_role} zone
                      </p>
                    </div>
                  </div>

                  <span
                    className={cn(
                      'inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium border select-none',
                      badge.classes
                    )}
                  >
                    <BadgeIcon className="h-2.5 w-2.5" />
                    <span>{badge.label}</span>
                  </span>
                </div>

                <p className="mt-2.5 text-xs text-muted-foreground leading-relaxed">
                  {station.description}
                </p>

                {/* Active task in workstation */}
                {activeTask ? (
                  <div className="mt-3 p-2.5 rounded bg-surface-raised border border-border/80 space-y-1">
                    <span className="text-[10px] uppercase font-semibold text-accent block">
                      Active Operation
                    </span>
                    <span className="text-xs font-medium text-foreground block truncate">
                      {activeTask.title}
                    </span>
                    {activeTask.progress_details && (
                      <span className="text-[11px] text-muted-foreground block line-clamp-2">
                        {activeTask.progress_details}
                      </span>
                    )}
                  </div>
                ) : (
                  <div className="mt-3 p-2.5 rounded border border-dashed border-border text-[11px] text-muted-foreground">
                    {station.queued_task_ids.length > 0
                      ? `${station.queued_task_ids.length} milestone tasks queued`
                      : station.status === 'completed'
                      ? 'Milestone completed successfully'
                      : 'Standby for stage invocation'}
                  </div>
                )}
              </div>

              {/* Station footer action */}
              <div className="mt-3.5 pt-2.5 border-t border-border flex items-center justify-between text-xs">
                <button
                  type="button"
                  onClick={() => onSelectRole(station.assigned_role)}
                  className="inline-flex items-center gap-1 text-[11px] font-medium text-accent hover:underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring rounded"
                >
                  <span>Inspect Agent</span>
                  <ArrowRight className="h-3 w-3" />
                </button>

                <span className="text-[10px] font-mono text-muted-foreground">
                  ID: {station.id}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
