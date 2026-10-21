'use client';

import * as React from 'react';
import {
  Briefcase,
  Compass,
  Palette,
  Terminal,
  ShieldCheck,
  Eye,
  Rocket,
  User,
  Activity,
  CheckCircle2,
  AlertCircle,
  Clock,
  Ban,
  XCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { AgentRole, EmployeeStatus, OfficeEmployeeState } from '@/features/office/types';

export interface EmployeeRosterProps {
  employees: OfficeEmployeeState[];
  selectedRole: AgentRole | null;
  onSelectEmployee: (employee: OfficeEmployeeState) => void;
}

export function getRoleIcon(role: AgentRole) {
  switch (role) {
    case 'manager':
      return Briefcase;
    case 'pm':
      return Compass;
    case 'designer':
      return Palette;
    case 'builder':
      return Terminal;
    case 'qa':
      return ShieldCheck;
    case 'reviewer':
      return Eye;
    case 'devops':
      return Rocket;
    default:
      return User;
  }
}

export function getEmployeeStatusBadge(status: EmployeeStatus) {
  switch (status) {
    case 'working':
      return {
        label: 'Working',
        icon: Activity,
        classes: 'bg-accent/10 border-accent/30 text-accent dark:text-[#6CB3A8]',
      };
    case 'waiting_approval':
      return {
        label: 'Awaiting Sign-off',
        icon: AlertCircle,
        classes: 'bg-warning-surface border-warning/40 text-warning dark:text-[#E29D86]',
      };
    case 'reviewing':
      return {
        label: 'Reviewing',
        icon: Eye,
        classes: 'bg-accent/10 border-accent/30 text-accent',
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
    case 'walking':
      return {
        label: 'Transit',
        icon: Clock,
        classes: 'bg-surface-raised border-border text-muted-foreground',
      };
    case 'idle':
    default:
      return {
        label: 'Idle / Standby',
        icon: Clock,
        classes: 'bg-surface-raised border-border text-muted-foreground',
      };
  }
}

export function EmployeeRoster({
  employees,
  selectedRole,
  onSelectEmployee,
}: EmployeeRosterProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Agency Team Roster</h3>
          <p className="text-xs text-muted-foreground">
            Authoritative logical roles and autonomous agents active on this project.
          </p>
        </div>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-surface-raised border border-border text-muted-foreground">
          {employees.length} members
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {employees.map((employee) => {
          const isSelected = selectedRole === employee.role;
          const RoleIcon = getRoleIcon(employee.role);
          const statusBadge = getEmployeeStatusBadge(employee.status);
          const StatusIcon = statusBadge.icon;

          return (
            <button
              key={employee.role}
              type="button"
              onClick={() => onSelectEmployee(employee)}
              className={cn(
                'group flex flex-col justify-between text-left p-3.5 rounded-lg border bg-surface transition-all outline-none',
                'hover:border-accent/40 hover:bg-surface-raised/60 focus-visible:ring-2 focus-visible:ring-ring',
                isSelected
                  ? 'border-accent ring-1 ring-accent bg-accent/5 dark:bg-accent/10 shadow-sm'
                  : 'border-border'
              )}
              aria-pressed={isSelected}
              aria-label={`Inspect ${employee.name}, ${employee.title}`}
            >
              {/* Header: Avatar, Name, Role */}
              <div className="flex items-start gap-3 w-full">
                <div
                  className={cn(
                    'flex h-10 w-10 shrink-0 items-center justify-center rounded-md border transition-colors',
                    isSelected
                      ? 'bg-accent text-accent-foreground border-accent'
                      : 'bg-surface-raised border-border text-foreground group-hover:border-accent/30'
                  )}
                >
                  <RoleIcon className="h-5 w-5" aria-hidden="true" />
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="font-medium text-xs text-foreground truncate">
                      {employee.name}
                    </span>
                    {employee.is_logical_role && (
                      <span className="text-[9px] uppercase tracking-wider font-semibold px-1 py-0.2 rounded bg-muted/20 border border-border text-muted-foreground">
                        Gate
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-muted-foreground truncate">{employee.title}</p>
                </div>
              </div>

              {/* Status and Activity Snippet */}
              <div className="mt-3 pt-2.5 border-t border-border/80 w-full flex items-center justify-between gap-2">
                <span
                  className={cn(
                    'inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium border select-none',
                    statusBadge.classes
                  )}
                >
                  <StatusIcon className="h-2.5 w-2.5 shrink-0" aria-hidden="true" />
                  <span>{statusBadge.label}</span>
                </span>

                <span className="text-[10px] text-muted-foreground font-mono truncate">
                  {employee.workstation.replace('_', ' ')}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
