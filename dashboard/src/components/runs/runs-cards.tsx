'use client';

import * as React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  Clock,
  ArrowRight,
  ExternalLink,
  AlertTriangle,
  Building2,
  Terminal,
  Globe,
  Layers,
  CheckCircle2,
} from 'lucide-react';
import { GlowCard } from '@/components/framer/glow-card';
import { StatusBadge } from '@/components/ui/status-badge';
import { EmptyState } from '@/components/ui/empty-state';
import { containerStaggerVariants, itemFadeUpVariants } from '@/lib/motion';
import type { RunResponse } from '@/features/runs/types';
import { cn } from '@/lib/utils';

export interface RunsCardsProps {
  runs: RunResponse[];
  isLoading?: boolean;
}

const STAGES = [
  { key: 'planning', label: 'Plan' },
  { key: 'prototyping', label: 'Design' },
  { key: 'building', label: 'Code' },
  { key: 'testing', label: 'QA' },
  { key: 'reviewing', label: 'Gate' },
  { key: 'deploying', label: 'Deploy' },
];

function getStageIndex(stage: string): number {
  const s = stage.toLowerCase();
  if (s.includes('plan')) return 0;
  if (s.includes('proto') || s.includes('design')) return 1;
  if (s.includes('build') || s.includes('code')) return 2;
  if (s.includes('qa') || s.includes('test')) return 3;
  if (s.includes('review') || s.includes('approv')) return 4;
  if (s.includes('deploy') || s.includes('complet')) return 5;
  return 0;
}

export function RunsCards({ runs, isLoading = false }: RunsCardsProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="h-56 rounded-xl border border-border bg-surface-raised/40 animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (runs.length === 0) {
    return (
      <EmptyState
        title="No runs match criteria"
        description="Try adjusting your filter settings or search query."
      />
    );
  }

  return (
    <motion.div
      variants={containerStaggerVariants}
      initial="hidden"
      animate="visible"
      className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
    >
      {runs.map((run) => {
        const stageIdx = getStageIndex(run.current_stage);
        const isCompleted = run.status.toUpperCase() === 'COMPLETED';
        const isFailed = ['FAILED', 'CANCELLED'].includes(run.status.toUpperCase());
        const isBlocked = run.status.toUpperCase() === 'AWAITING_APPROVAL';

        return (
          <motion.div key={run.run_id} variants={itemFadeUpVariants}>
            <GlowCard className="p-4 flex flex-col justify-between min-h-[220px] rounded-xl border border-border bg-surface transition-all hover:border-accent/40">
              <div className="space-y-3">
                {/* Header: Project and Status */}
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <Link
                      href={`/runs/${encodeURIComponent(run.run_id)}`}
                      className="font-semibold text-sm text-foreground hover:text-accent transition-colors block truncate"
                    >
                      {run.project_id}
                    </Link>
                    <span className="text-[10px] font-mono text-muted-foreground block truncate">
                      ID: {run.run_id.slice(0, 16)}...
                    </span>
                  </div>
                  <StatusBadge status={run.status} size="sm" />
                </div>

                {/* Stage Pipeline Mini-Stepper */}
                <div className="space-y-1.5 pt-1">
                  <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                    <span className="font-medium text-foreground capitalize">
                      Stage: {run.current_stage.replace('_', ' ')}
                    </span>
                    {(run.current_revision ?? 0) > 0 && (
                      <span className="font-mono text-[10px] text-muted-foreground">
                        rev #{run.current_revision}
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-6 gap-1 h-1.5 rounded-full overflow-hidden bg-surface-raised border border-border">
                    {STAGES.map((st, i) => {
                      const isPast = isCompleted || i < stageIdx;
                      const isCurrent = !isCompleted && !isFailed && i === stageIdx;
                      return (
                        <div
                          key={st.key}
                          title={st.label}
                          className={cn(
                            'h-full transition-colors',
                            isPast && 'bg-accent/80',
                            isCurrent && (isBlocked ? 'bg-warning animate-pulse' : 'bg-accent animate-pulse'),
                            !isPast && !isCurrent && isFailed && i === stageIdx ? 'bg-danger' : '',
                            !isPast && !isCurrent && (!isFailed || i !== stageIdx) ? 'bg-transparent' : ''
                          )}
                        />
                      );
                    })}
                  </div>
                </div>

                {/* Failure or Blocker warning */}
                {run.failure_details?.reason && (
                  <div className="text-[11px] text-danger bg-danger-surface/60 border border-danger/30 rounded-md p-2 flex items-center gap-1.5">
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate">{run.failure_details.reason}</span>
                  </div>
                )}

                {/* Live Preview / Production link badge if present */}
                {(run.production_url || run.preview_url) && (
                  <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                    <Globe className="h-3 w-3 text-accent shrink-0" />
                    <a
                      href={run.production_url || run.preview_url || '#'}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="truncate text-accent hover:underline font-mono text-[10px]"
                    >
                      {run.production_url || run.preview_url}
                    </a>
                  </div>
                )}
              </div>

              {/* Card Footer: Metadata & Quick Direct Action Links */}
              <div className="mt-4 pt-3 border-t border-border flex items-center justify-between text-[11px]">
                <span className="text-muted-foreground font-mono flex items-center gap-1 text-[10px]">
                  <Clock className="h-3 w-3" />
                  {new Date(run.created_at).toLocaleDateString()}
                </span>

                <div className="flex items-center gap-2">
                  <Link
                    href={`/office?runId=${encodeURIComponent(run.run_id)}`}
                    className="inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium text-muted-foreground hover:text-foreground hover:bg-surface-raised transition-colors border border-border"
                    title="View in Virtual Office"
                  >
                    <Building2 className="h-3 w-3" />
                    <span>Office</span>
                  </Link>

                  <Link
                    href={`/runs/${encodeURIComponent(run.run_id)}`}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-semibold text-accent hover:bg-accent/10 transition-colors border border-accent/25"
                  >
                    <span>Hub</span>
                    <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
              </div>
            </GlowCard>
          </motion.div>
        );
      })}
    </motion.div>
  );
}
