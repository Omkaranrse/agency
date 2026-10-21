'use client';

import * as React from 'react';
import Link from 'next/link';
import {
  Plus,
  RefreshCw,
  LayoutGrid,
  Table as TableIcon,
  Activity,
  CheckCircle2,
  AlertCircle,
  XCircle,
  Layers,
  ArrowRight,
} from 'lucide-react';
import { PageHeader } from '@/components/ui/page-header';
import { Button } from '@/components/ui/button';
import { ErrorState } from '@/components/ui/error-state';
import { RunsTable } from '@/components/runs/runs-table';
import { RunsCards } from '@/components/runs/runs-cards';
import { RunsFilters } from '@/components/runs/runs-filters';
import { AnimatedCounter } from '@/components/framer/animated-counter';
import { GlowCard } from '@/components/framer/glow-card';
import { SlidingTabs } from '@/components/framer/sliding-tabs';
import { AIManagerAvatar } from '@/components/manager/ai-manager-avatar';
import { useRunsList } from '@/features/runs/queries';
import { parseApiError } from '@/lib/api/config';
import type { RunState } from '@/features/runs/types';
import { cn } from '@/lib/utils';

export default function RunsPage() {
  const [page, setPage] = React.useState(0);
  const [pageSize] = React.useState(20);
  const [status, setStatus] = React.useState<RunState | undefined>(undefined);
  const [search, setSearch] = React.useState('');
  const [viewMode, setViewMode] = React.useState<'table' | 'cards'>('cards');

  const { data, isLoading, error, refetch, isFetching } = useRunsList({
    limit: pageSize,
    offset: page * pageSize,
    status: status,
  });

  const parsedError = error ? parseApiError(error) : null;
  const allRuns = React.useMemo(() => data?.items ?? [], [data?.items]);

  // Filter items locally by search query if user typed search text
  const filteredRuns = React.useMemo(() => {
    if (!search.trim()) return allRuns;
    const q = search.toLowerCase().trim();
    return allRuns.filter(
      (r) =>
        r.project_id.toLowerCase().includes(q) ||
        r.run_id.toLowerCase().includes(q) ||
        r.status.toLowerCase().includes(q)
    );
  }, [allRuns, search]);

  // Derive operations metrics
  const metrics = React.useMemo(() => {
    const total = data?.pagination?.total ?? allRuns.length;
    const active = allRuns.filter((r) =>
      ['CREATED', 'PLANNING', 'PROTOTYPING', 'BUILDING', 'TESTING', 'DEPLOYING'].includes(
        r.status.toUpperCase()
      )
    ).length;
    const pendingApproval = allRuns.filter(
      (r) => r.status.toUpperCase() === 'AWAITING_APPROVAL'
    ).length;
    const completed = allRuns.filter((r) => r.status.toUpperCase() === 'COMPLETED').length;
    const failed = allRuns.filter((r) =>
      ['FAILED', 'CANCELLED'].includes(r.status.toUpperCase())
    ).length;

    return { total, active, pendingApproval, completed, failed };
  }, [allRuns, data?.pagination?.total]);

  const isFiltered = Boolean(status || search.trim());

  const handleResetFilters = () => {
    setStatus(undefined);
    setSearch('');
    setPage(0);
  };

  const handleStatusChange = (newStatus: RunState | undefined) => {
    setStatus(newStatus);
    setPage(0);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="Mission Control"
        description="Monitor, orchestrate, and audit automated multi-agent website generation runs across all pipeline stages."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              isLoading={isFetching && !isLoading}
              title="Refresh runs list"
              className="h-8 text-xs gap-1.5"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Sync</span>
            </Button>

            <Button asChild size="sm" className="h-8 text-xs gap-1.5">
              <Link href="/new-run">
                <Plus className="h-3.5 w-3.5" aria-hidden="true" />
                <span>New Run</span>
              </Link>
            </Button>
          </div>
        }
      />

      {/* Top Operations Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
        {/* Total Runs */}
        <div className="p-3.5 rounded-xl border border-border bg-surface hover:border-accent/30 transition-all shadow-xs">
          <div className="flex items-center justify-between text-muted-foreground text-xs">
            <span className="font-medium">Total Runs</span>
            <Layers className="h-3.5 w-3.5 text-muted-foreground" />
          </div>
          <div className="mt-2 font-mono text-2xl font-semibold text-foreground tracking-tight">
            <AnimatedCounter value={metrics.total} />
          </div>
          <span className="text-[10px] text-muted-foreground mt-1 block">Recorded in database</span>
        </div>

        {/* Active Pipelines */}
        <div className="p-3.5 rounded-xl border border-border bg-surface hover:border-accent/40 transition-all shadow-xs">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-accent">Active Pipelines</span>
            <Activity className="h-3.5 w-3.5 text-accent" />
          </div>
          <div className="mt-2 font-mono text-2xl font-semibold text-accent tracking-tight">
            <AnimatedCounter value={metrics.active} />
          </div>
          <span className="text-[10px] text-muted-foreground mt-1 block">Running across agents</span>
        </div>

        {/* Pending Approvals */}
        <div className="p-3.5 rounded-xl border border-border bg-surface hover:border-warning/40 transition-all shadow-xs">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-warning">Pending Approvals</span>
            <AlertCircle className="h-3.5 w-3.5 text-warning" />
          </div>
          <div className="mt-2 font-mono text-2xl font-semibold text-warning tracking-tight">
            <AnimatedCounter value={metrics.pendingApproval} />
          </div>
          <span className="text-[10px] text-muted-foreground mt-1 block">Require human review</span>
        </div>

        {/* Delivered Projects */}
        <div className="p-3.5 rounded-xl border border-border bg-surface hover:border-success/40 transition-all shadow-xs">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-success">Delivered Projects</span>
            <CheckCircle2 className="h-3.5 w-3.5 text-success" />
          </div>
          <div className="mt-2 font-mono text-2xl font-semibold text-success tracking-tight">
            <AnimatedCounter value={metrics.completed} />
          </div>
          <span className="text-[10px] text-muted-foreground mt-1 block">Production deployments</span>
        </div>
      </div>

      {/* AI Manager Contextual Helper */}
      <div className="p-3 rounded-xl border border-border bg-surface-raised/40 flex items-center justify-between gap-3 text-xs shadow-xs">
        <div className="flex items-center gap-3 min-w-0">
          <AIManagerAvatar size="sm" showBadge={false} />
          <div className="min-w-0">
            <span className="font-semibold text-foreground mr-1.5 text-xs">Alex Morgan (Manager):</span>
            <span className="text-muted-foreground text-xs">
              {metrics.pendingApproval > 0
                ? `${metrics.pendingApproval} run(s) are awaiting operator review. I can summarize the diffs for you in the AI Manager.`
                : `${metrics.active} active pipeline(s) running across agent workstations. Need to inspect telemetry or launch a new brief?`}
            </span>
          </div>
        </div>
        <Link
          href="/manager"
          className="shrink-0 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium text-accent hover:bg-accent/10 border border-accent/25 transition-colors"
        >
          <span>Ask Alex</span>
          <ArrowRight className="h-3 w-3" />
        </Link>
      </div>

      {/* Filter and View Toggle Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
        <div className="flex-1 min-w-0">
          <RunsFilters
            search={search}
            onSearchChange={setSearch}
            status={status}
            onStatusChange={handleStatusChange}
            onReset={handleResetFilters}
            isFiltered={isFiltered}
          />
        </div>

        {/* View Switcher Tabs */}
        <div className="shrink-0 self-end sm:self-center">
          <SlidingTabs
            tabs={[
              { id: 'cards', label: 'Cards', icon: LayoutGrid },
              { id: 'table', label: 'Table', icon: TableIcon },
            ]}
            activeTab={viewMode}
            onChange={(id) => setViewMode(id as 'table' | 'cards')}
            layoutId="runs-view-switcher"
          />
        </div>
      </div>

      {/* Main Content Area */}
      {parsedError ? (
        <ErrorState
          title="Failed to retrieve runs"
          message={parsedError.message}
          referenceId={parsedError.code || `HTTP_${parsedError.status}`}
          onRetry={() => refetch()}
          isRetrying={isFetching}
        />
      ) : viewMode === 'cards' ? (
        <RunsCards runs={filteredRuns} isLoading={isLoading} />
      ) : (
        <RunsTable
          runs={filteredRuns}
          isLoading={isLoading}
          isFiltered={isFiltered}
          onResetFilters={handleResetFilters}
          page={page}
          pageSize={pageSize}
          total={data?.pagination?.total ?? 0}
          hasNext={data?.pagination?.has_next ?? false}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}
