'use client';

import * as React from 'react';
import Link from 'next/link';
import { useSearchParams, useRouter } from 'next/navigation';
import {
  RefreshCw,
  LayoutGrid,
  Table as TableIcon,
  AlertTriangle,
  ExternalLink,
  Wifi,
  WifiOff,
  Layers,
  Sparkles,
  Box,
} from 'lucide-react';
import { PageHeader } from '@/components/ui/page-header';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/ui/error-state';
import { EmptyState } from '@/components/ui/empty-state';
import { StatusBadge } from '@/components/ui/status-badge';
import { EmployeeRoster } from '@/components/office/employee-roster';
import { EmployeeDetailDrawer } from '@/components/office/employee-detail-drawer';
import { WorkstationsPanel } from '@/components/office/workstations-panel';
import { TasksOverviewTable } from '@/components/office/tasks-overview-table';
import { ThreeOfficeWrapper } from '@/components/office/three-office-wrapper';
import { useRunsList } from '@/features/runs/queries';
import { useRunEventStream } from '@/features/runs/event-stream';
import { useOfficeState } from '@/features/office/queries';
import type { AgentRole, OfficeEmployeeState } from '@/features/office/types';
import { cn } from '@/lib/utils';

function OfficePageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryRunId = searchParams.get('runId') || '';

  // 1. Fetch available runs for the run selector
  const { data: runsData, isLoading: isRunsLoading } = useRunsList({ limit: 50 });
  const runs = React.useMemo(() => runsData?.items || [], [runsData?.items]);

  // 2. Active run
  const activeRunId = React.useMemo(() => {
    if (queryRunId && runs.some((r) => r.run_id === queryRunId)) {
      return queryRunId;
    }
    return runs.length > 0 ? runs[0].run_id : '';
  }, [queryRunId, runs]);

  const handleSelectRun = (newRunId: string) => {
    router.push(`/office?runId=${encodeURIComponent(newRunId)}`);
  };

  // 3. Office state query for active run
  const {
    data: officeState,
    isLoading: isOfficeLoading,
    error: officeError,
    refetch: refetchOffice,
    isFetching: isOfficeFetching,
  } = useOfficeState(activeRunId || undefined);

  // 4. Live SSE integration with trailing debounce
  const debounceTimerRef = React.useRef<NodeJS.Timeout | null>(null);
  const handleEvent = React.useCallback(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    debounceTimerRef.current = setTimeout(() => {
      refetchOffice();
    }, 800);
  }, [refetchOffice]);

  React.useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  const { status: streamStatus } = useRunEventStream({
    runId: activeRunId,
    enabled: Boolean(activeRunId),
    onEvent: handleEvent,
  });

  // 5. Drawer & View mode state
  const [selectedRole, setSelectedRole] = React.useState<AgentRole | null>(null);
  const [viewMode, setViewMode] = React.useState<'3d' | 'overview' | 'table'>('3d');

  const selectedEmployee = React.useMemo(() => {
    if (!selectedRole || !officeState) return null;
    return officeState.employees.find((e) => e.role === selectedRole) || null;
  }, [selectedRole, officeState]);

  const selectedTask = React.useMemo(() => {
    if (!selectedEmployee || !officeState) return null;
    return (
      officeState.tasks.find((t) => t.agent_role === selectedEmployee.role) || null
    );
  }, [selectedEmployee, officeState]);

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <PageHeader
        title="3D Virtual Office"
        description="Real-time multi-agent spatial floor with live workstation telemetry and Minecraft-style 3D models."
        actions={
          <div className="flex items-center gap-2">
            {/* Run Selector */}
            {runs.length > 0 && (
              <div className="flex items-center gap-2">
                <label
                  htmlFor="office-run-selector"
                  className="text-xs font-mono text-muted-foreground hidden sm:inline"
                >
                  Active Run:
                </label>
                <select
                  id="office-run-selector"
                  value={activeRunId}
                  onChange={(e) => handleSelectRun(e.target.value)}
                  className="text-xs bg-surface border border-border rounded px-2.5 py-1.5 text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring font-mono"
                >
                  {runs.map((r) => (
                    <option key={r.run_id} value={r.run_id}>
                      {r.project_id} ({r.status})
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* View Mode Switcher */}
            <div className="flex items-center p-0.5 rounded-lg border border-border bg-surface">
              <button
                type="button"
                onClick={() => setViewMode('3d')}
                className={cn(
                  'flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors',
                  viewMode === '3d'
                    ? 'bg-accent text-accent-foreground font-semibold shadow-xs'
                    : 'text-muted-foreground hover:text-foreground'
                )}
                title="3D Spatial Voxel Canvas"
              >
                <Box className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">3D Office</span>
              </button>
              <button
                type="button"
                onClick={() => setViewMode('overview')}
                className={cn(
                  'flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors',
                  viewMode === 'overview'
                    ? 'bg-accent text-accent-foreground font-semibold shadow-xs'
                    : 'text-muted-foreground hover:text-foreground'
                )}
                title="2D Workstation Stations"
              >
                <LayoutGrid className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Stations</span>
              </button>
              <button
                type="button"
                onClick={() => setViewMode('table')}
                className={cn(
                  'flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors',
                  viewMode === 'table'
                    ? 'bg-accent text-accent-foreground font-semibold shadow-xs'
                    : 'text-muted-foreground hover:text-foreground'
                )}
                title="Detailed Tasks Table"
              >
                <TableIcon className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Tasks</span>
              </button>
            </div>

            {/* Refresh */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetchOffice()}
              isLoading={isOfficeFetching && !isOfficeLoading}
              title="Refresh office state"
              className="h-8 text-xs gap-1.5"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Sync</span>
            </Button>
          </div>
        }
      />

      {/* Main Content Area */}
      {viewMode === '3d' ? (
        <div className="space-y-6">
          {/* Dedicated 3D Office Canvas Box */}
          <ThreeOfficeWrapper
            employees={officeState?.employees ?? []}
            workstations={officeState?.workstations ?? []}
            selectedRole={selectedRole}
            onSelectRole={(role) => setSelectedRole(role)}
            onSwitchToTableView={() => setViewMode('table')}
          />

          {/* Employee Roster Card below 3D scene */}
          <div className="p-4 rounded-xl border border-border bg-surface shadow-xs">
            <h3 className="text-xs font-semibold text-foreground mb-3 flex items-center justify-between">
              <span>Stationed Agent Team ({officeState?.employees.length ?? 7})</span>
              <span className="text-[10px] font-mono text-muted-foreground">Click agent to inspect</span>
            </h3>
            <EmployeeRoster
              employees={officeState?.employees ?? []}
              selectedRole={selectedRole}
              onSelectEmployee={(emp) => setSelectedRole(emp.role)}
            />
          </div>
        </div>
      ) : viewMode === 'overview' ? (
        <div className="space-y-6">
          <WorkstationsPanel
            workstations={officeState?.workstations ?? []}
            tasks={officeState?.tasks ?? []}
            onSelectRole={(role) => setSelectedRole(role)}
          />
          <EmployeeRoster
            employees={officeState?.employees ?? []}
            selectedRole={selectedRole}
            onSelectEmployee={(emp) => setSelectedRole(emp.role)}
          />
        </div>
      ) : (
        <div className="space-y-6">
          <TasksOverviewTable
            tasks={officeState?.tasks ?? []}
            onSelectRole={(role) => setSelectedRole(role)}
          />
        </div>
      )}

      {/* Slide-out detail drawer */}
      <EmployeeDetailDrawer
        employee={selectedEmployee}
        task={selectedTask}
        runId={activeRunId}
        onClose={() => setSelectedRole(null)}
      />
    </div>
  );
}

export default function OfficePage() {
  return (
    <React.Suspense
      fallback={
        <div className="space-y-6 p-6">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-[460px] w-full rounded-2xl" />
        </div>
      }
    >
      <OfficePageContent />
    </React.Suspense>
  );
}
