'use client';

import * as React from 'react';
import { motion } from 'framer-motion';
import {
  CheckCircle2,
  AlertCircle,
  XCircle,
  FileText,
  Palette,
  ShieldAlert,
  Code2,
  CheckCheck,
  Rocket,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { RunResponse } from '@/features/runs/types';

export interface PipelineStepperProps {
  run: RunResponse;
  className?: string;
}

interface StepDef {
  key: string;
  label: string;
  shortLabel: string;
  icon: React.ComponentType<{ className?: string }>;
}

const PIPELINE_STEPS: StepDef[] = [
  { key: 'planning', label: '1. Specification', shortLabel: 'Spec', icon: FileText },
  { key: 'prototyping', label: '2. Prototype', shortLabel: 'Design', icon: Palette },
  { key: 'review', label: '3. Review Gate', shortLabel: 'Approval', icon: ShieldAlert },
  { key: 'building', label: '4. Code Build', shortLabel: 'Build', icon: Code2 },
  { key: 'testing', label: '5. QA Audit', shortLabel: 'QA', icon: CheckCheck },
  { key: 'deploying', label: '6. Edge Deploy', shortLabel: 'Deploy', icon: Rocket },
];

function getStageStepIndex(stage: string, status: string): number {
  const s = (stage || '').toLowerCase();
  const st = (status || '').toUpperCase();

  if (st === 'COMPLETED') return 6; // All complete

  if (s.includes('deploy')) return 5;
  if (s.includes('test') || s.includes('qa')) return 4;
  if (s.includes('build')) return 3;
  if (s.includes('review') || st === 'AWAITING_APPROVAL') return 2;
  if (s.includes('proto') || s.includes('design')) return 1;
  return 0; // planning/spec
}

export function PipelineStepper({ run, className }: PipelineStepperProps) {
  const currentStepIdx = getStageStepIndex(run.current_stage, run.status);
  const isCompleted = run.status.toUpperCase() === 'COMPLETED';
  const isFailed = ['FAILED', 'CANCELLED'].includes(run.status.toUpperCase());
  const isAwaitingApproval = run.status.toUpperCase() === 'AWAITING_APPROVAL';

  return (
    <div
      className={cn(
        'w-full rounded-xl border border-border bg-surface/80 backdrop-blur-sm p-3.5 shadow-xs overflow-x-auto',
        className
      )}
    >
      <div className="flex items-center justify-between min-w-[620px] gap-2">
        {PIPELINE_STEPS.map((step, idx) => {
          const Icon = step.icon;
          const isPast = idx < currentStepIdx || isCompleted;
          const isCurrent = idx === currentStepIdx && !isCompleted;
          const isStepFailed = isCurrent && isFailed;
          const isStepBlocked = isCurrent && isAwaitingApproval;

          return (
            <React.Fragment key={step.key}>
              {/* Step item */}
              <div className="flex items-center gap-2 select-none group">
                <div
                  className={cn(
                    'relative flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border text-xs font-mono font-medium transition-all duration-200',
                    isPast && 'border-success/40 bg-success/10 text-success shadow-xs',
                    isCurrent && !isStepFailed && !isStepBlocked &&
                      'border-accent bg-accent/15 text-accent shadow-xs ring-2 ring-accent/30',
                    isStepBlocked &&
                      'border-warning/50 bg-warning/15 text-warning ring-2 ring-warning/30 animate-pulse',
                    isStepFailed &&
                      'border-danger/50 bg-danger/15 text-danger ring-2 ring-danger/30',
                    !isPast && !isCurrent &&
                      'border-border/80 bg-surface-raised/40 text-muted-foreground'
                  )}
                >
                  {isPast ? (
                    <CheckCircle2 className="h-4 w-4" />
                  ) : isStepFailed ? (
                    <XCircle className="h-4 w-4" />
                  ) : isStepBlocked ? (
                    <AlertCircle className="h-4 w-4" />
                  ) : (
                    <Icon className="h-3.5 w-3.5" />
                  )}

                  {isCurrent && !isStepFailed && (
                    <span className="absolute -top-1 -right-1 flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75" />
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-accent" />
                    </span>
                  )}
                </div>

                <div className="flex flex-col min-w-0">
                  <span
                    className={cn(
                      'text-xs tracking-tight whitespace-nowrap font-medium',
                      isPast && 'text-foreground/90 font-medium',
                      isCurrent && 'text-foreground font-semibold',
                      !isPast && !isCurrent && 'text-muted-foreground'
                    )}
                  >
                    {step.label}
                  </span>
                  <span className="text-[10px] font-mono text-muted-foreground/80 leading-none">
                    {isPast
                      ? 'Completed'
                      : isStepBlocked
                      ? 'Action Required'
                      : isStepFailed
                      ? 'Failed'
                      : isCurrent
                      ? 'In Progress'
                      : 'Queued'}
                  </span>
                </div>
              </div>

              {/* Connecting rail */}
              {idx < PIPELINE_STEPS.length - 1 && (
                <div
                  className={cn(
                    'flex-1 h-[2px] mx-1 rounded-full min-w-[20px] transition-colors',
                    idx < currentStepIdx
                      ? 'bg-success/50'
                      : idx === currentStepIdx
                      ? 'bg-gradient-to-r from-accent to-border'
                      : 'bg-border/60'
                  )}
                />
              )}
            </React.Fragment>
          );
        })}

        {/* Current Revision Indicator */}
        {Boolean(run.current_revision && run.current_revision > 0) && (
          <div className="ml-2 pl-3 border-l border-border shrink-0">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-medium border border-accent/40 bg-accent/10 text-accent">
              Rev #{run.current_revision}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

export default PipelineStepper;
