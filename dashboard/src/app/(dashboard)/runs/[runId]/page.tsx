'use client';

import * as React from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { ArrowLeft, RefreshCw, XCircle, AlertCircle } from 'lucide-react';
import { PageHeader } from '@/components/ui/page-header';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/ui/error-state';
import { RunTimeline } from '@/components/runs/run-timeline';
import { RunPreview } from '@/components/runs/run-preview';
import { RunDetailsPanel } from '@/components/runs/run-details-panel';
import { ApprovalPanel } from '@/components/runs/approval-panel';
import { CompletedRunPanel } from '@/components/runs/completed-run-panel';
import { RunStatusBadge } from '@/components/runs/run-status';
import { useRunDetails } from '@/features/runs/queries';
import { useRunEventStream } from '@/features/runs/event-stream';
import { parseApiError } from '@/lib/api/config';

export default function RunDetailPage() {
  const params = useParams();
  const runId = typeof params?.runId === 'string' ? params.runId : '';

  const {
    data: run,
    isLoading: isRunLoading,
    error: runError,
    refetch: refetchRun,
    isFetching: isRunFetching,
  } = useRunDetails(runId);

  // Hook up SSE live events stream
  const handleEvent = React.useCallback(() => {
    // Reconcile REST run state when events arrive
    refetchRun();
  }, [refetchRun]);

  const {
    events,
    status: streamStatus,
    error: streamError,
    reconnect: reconnectStream,
  } = useRunEventStream({
    runId,
    enabled: Boolean(runId),
    onEvent: handleEvent,
  });

  const parsedError = runError ? parseApiError(runError) : null;

  if (isRunLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-border">
          <div className="space-y-2">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-72" />
          </div>
          <Skeleton className="h-8 w-24" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <Skeleton className="lg:col-span-4 h-96" />
          <Skeleton className="lg:col-span-5 h-96" />
          <Skeleton className="lg:col-span-3 h-96" />
        </div>
      </div>
    );
  }

  if (parsedError || !run) {
    return (
      <div className="space-y-6">
        <div className="pb-4 border-b border-border">
          <Button asChild variant="outline" size="sm">
            <Link href="/runs" className="inline-flex items-center gap-1.5">
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Back to runs</span>
            </Link>
          </Button>
        </div>
        <ErrorState
          title="Failed to load run details"
          message={parsedError?.message || 'Run aggregate could not be retrieved from the API.'}
          referenceId={parsedError?.code || `RUN_${runId}`}
          onRetry={() => refetchRun()}
          isRetrying={isRunFetching}
        />
      </div>
    );
  }

  const isAwaitingApproval =
    run.status.toUpperCase() === 'AWAITING_APPROVAL' || run.approval_state === 'pending';
  const isCompleted = run.status.toUpperCase() === 'COMPLETED';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="space-y-6 pb-12"
    >
      {/* Page Header */}
      <PageHeader
        title={run.project_id}
        description={`Run ID: ${run.run_id}`}
        breadcrumbs={
          <div className="flex items-center gap-2">
            <Button asChild variant="ghost" size="sm" className="h-6 px-1.5 text-xs text-muted-foreground hover:text-accent">
              <Link href="/runs" className="inline-flex items-center gap-1 font-mono">
                <ArrowLeft className="h-3 w-3" />
                <span>RUNS</span>
              </Link>
            </Button>
            <span className="text-muted-foreground">/</span>
            <span className="font-mono text-xs text-foreground truncate max-w-[200px]">
              {run.project_id}
            </span>
          </div>
        }
        actions={
          <div className="flex items-center gap-2">
            <RunStatusBadge
              status={run.status}
              stage={run.current_stage}
              revision={run.current_revision}
            />

            <Button asChild variant="outline" size="sm" className="h-8 text-xs gap-1.5">
              <Link href={`/office?runId=${encodeURIComponent(run.run_id)}`}>
                <span>3D Office</span>
              </Link>
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => refetchRun()}
              isLoading={isRunFetching}
              title="Refresh run state"
              className="h-8 hover:border-accent hover:text-accent"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
          </div>
        }
      />

      {/* Screen 4: Approval Gate Panel (prominently rendered when awaiting approval) */}
      {isAwaitingApproval && (
        <ApprovalPanel run={run} onRefreshRun={() => refetchRun()} />
      )}

      {/* Screen 5: Completed Run Panel (prominently rendered when completed) */}
      {isCompleted && <CompletedRunPanel run={run} />}

      {/* Screen 3: Three-Region Workspace (Timeline / Preview / Details) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
        {/* Left Region: Activity Timeline (4 cols on lg) */}
        <div className="lg:col-span-4 h-full">
          <RunTimeline
            events={events}
            status={streamStatus}
            streamError={streamError}
            onReconnect={reconnectStream}
            currentStage={run.current_stage}
          />
        </div>

        {/* Center Region: Prototype Preview (5 cols on lg) */}
        <div className="lg:col-span-5 h-full">
          <RunPreview
            previewUrl={run.preview_url}
            status={run.status}
            currentStage={run.current_stage}
          />
        </div>

        {/* Right Region: Details & QA Tabs (3 cols on lg) */}
        <div className="lg:col-span-3 h-full">
          <RunDetailsPanel run={run} events={events} />
        </div>
      </div>
    </motion.div>
  );
}
