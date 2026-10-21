'use client';

import * as React from 'react';
import Link from 'next/link';
import { ChevronRight, Clock, DollarSign, Layers } from 'lucide-react';
import { DataTable, type ColumnDef } from '@/components/ui/data-table';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { RunStatusBadge } from './run-status';
import type { RunResponse } from '@/features/runs/types';

export interface RunsTableProps {
  runs: RunResponse[];
  isLoading: boolean;
  isFiltered: boolean;
  onResetFilters?: () => void;
  // Pagination
  page: number;
  pageSize: number;
  total: number;
  hasNext: boolean;
  onPageChange: (newPage: number) => void;
}

function formatDate(isoString: string): string {
  try {
    const d = new Date(isoString);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).format(d);
  } catch {
    return isoString;
  }
}

export function RunsTable({
  runs,
  isLoading,
  isFiltered,
  onResetFilters,
  page,
  pageSize,
  total,
  hasNext,
  onPageChange,
}: RunsTableProps) {
  const columns: ColumnDef<RunResponse>[] = [
    {
      id: 'project',
      header: 'Project / Client',
      cell: (run) => (
        <div className="min-w-[140px]">
          <Link
            href={`/runs/${run.run_id}`}
            className="font-medium text-foreground hover:text-accent transition-colors block truncate max-w-[200px]"
          >
            {run.project_id}
          </Link>
          <span className="font-mono text-[11px] text-muted-foreground block truncate max-w-[160px]">
            {run.run_id}
          </span>
        </div>
      ),
    },
    {
      id: 'status',
      header: 'Status',
      cell: (run) => (
        <RunStatusBadge
          status={run.status}
          stage={run.current_stage}
          revision={run.current_revision}
        />
      ),
    },
    {
      id: 'stage',
      header: 'Stage',
      cell: (run) => (
        <span className="text-xs text-muted-foreground capitalize">
          {run.current_stage.replace(/_/g, ' ')}
        </span>
      ),
    },
    {
      id: 'created_at',
      header: 'Created',
      cell: (run) => (
        <span className="text-[11px] text-muted-foreground font-mono">
          {formatDate(run.created_at)}
        </span>
      ),
    },
    {
      id: 'duration',
      header: 'Duration',
      cell: () => (
        <span
          className="text-muted-foreground text-xs font-mono"
          title="Workflow execution duration is not exposed by current API schema"
        >
          —
        </span>
      ),
    },
    {
      id: 'cost',
      header: 'Cost',
      cell: () => (
        <span
          className="text-muted-foreground text-xs font-mono"
          title="Token budget telemetry is tracked in backend LLM logs"
        >
          —
        </span>
      ),
    },
    {
      id: 'actions',
      header: 'Action',
      headerClassName: 'text-right',
      className: 'text-right',
      cell: (run) => (
        <div className="flex items-center justify-end gap-1.5">
          <Button asChild variant="ghost" size="sm" className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground">
            <Link href={`/office?runId=${encodeURIComponent(run.run_id)}`} title="View in 3D Office">
              Office
            </Link>
          </Button>
          <Button asChild variant="outline" size="sm" className="h-7 text-xs">
            <Link href={`/runs/${run.run_id}`} className="inline-flex items-center gap-1">
              <span>View</span>
              <ChevronRight className="h-3 w-3" />
            </Link>
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-3">
      <DataTable
        columns={columns}
        data={runs}
        keyExtractor={(item) => item.run_id}
        isLoading={isLoading}
        loadingRowCount={5}
        caption="List of client website generation runs"
        emptyState={
          isFiltered ? (
            <EmptyState
              icon={Layers}
              title="No runs match filter criteria"
              description="Try adjusting your search query or selecting a different status filter."
              action={
                onResetFilters && (
                  <Button variant="outline" size="sm" onClick={onResetFilters}>
                    Clear filters
                  </Button>
                )
              }
            />
          ) : (
            <EmptyState
              icon={Layers}
              title="No runs initiated yet"
              description="Get started by submitting a client website brief to trigger the automated delivery pipeline."
              action={
                <Button asChild size="sm">
                  <Link href="/new-run">Submit new brief</Link>
                </Button>
              }
            />
          )
        }
      />

      {/* Pagination Bar */}
      {total > 0 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-1 py-2 text-xs text-muted-foreground">
          <div>
            Showing <span className="font-mono text-foreground">{page * pageSize + 1}</span> to{' '}
            <span className="font-mono text-foreground">
              {Math.min((page + 1) * pageSize, total)}
            </span>{' '}
            of <span className="font-mono text-foreground">{total}</span> runs
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 0 || isLoading}
              onClick={() => onPageChange(page - 1)}
            >
              Previous
            </Button>
            <span className="font-mono text-xs px-2">Page {page + 1}</span>
            <Button
              variant="outline"
              size="sm"
              disabled={!hasNext || isLoading}
              onClick={() => onPageChange(page + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
