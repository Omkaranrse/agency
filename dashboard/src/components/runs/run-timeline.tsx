'use client';

import * as React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CheckCircle2,
  Clock,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Wifi,
  WifiOff,
  Radio,
  Activity,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { TextScramble } from '@/components/framer/text-scramble';
import { AnimatedCounter } from '@/components/framer/animated-counter';
import type { DomainEventEnvelope, EventStreamStatus } from '@/features/runs/types';

export interface RunTimelineProps {
  events: DomainEventEnvelope[];
  status: EventStreamStatus;
  streamError: string | null;
  onReconnect: () => void;
  currentStage: string;
}

function formatTime(isoString: string): string {
  try {
    const d = new Date(isoString);
    return new Intl.DateTimeFormat('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }).format(d);
  } catch {
    return isoString;
  }
}

function getEventMeta(eventType: string) {
  switch (eventType) {
    case 'RunStarted':
      return { label: 'Run Initialized', variant: 'info', icon: Radio, color: 'text-brand-blue border-brand-blue/40 bg-brand-blue/10' };
    case 'PlanningCompleted':
      return { label: 'Specification Formulated', variant: 'info', icon: CheckCircle2, color: 'text-brand-teal border-brand-teal/40 bg-brand-teal/10' };
    case 'PrototypeReady':
      return { label: 'Prototype Preview Ready', variant: 'warning', icon: AlertTriangle, color: 'text-warning border-warning/40 bg-warning/10' };
    case 'PrototypeApproved':
      return { label: 'Prototype Approved', variant: 'success', icon: CheckCircle2, color: 'text-success border-success/40 bg-success/10' };
    case 'RevisionRequested':
      return { label: 'Revision Requested', variant: 'warning', icon: AlertTriangle, color: 'text-warning border-warning/40 bg-warning/10' };
    case 'BuildStarted':
      return { label: 'Code Build Started', variant: 'info', icon: Activity, color: 'text-brand-blue border-brand-blue/40 bg-brand-blue/10' };
    case 'BuildCompleted':
      return { label: 'Build Completed', variant: 'success', icon: CheckCircle2, color: 'text-success border-success/40 bg-success/10' };
    case 'QAPassed':
      return { label: 'Automated QA Passed', variant: 'success', icon: CheckCircle2, color: 'text-success border-success/40 bg-success/10' };
    case 'QAFailed':
      return { label: 'QA Verification Failed', variant: 'danger', icon: XCircle, color: 'text-error border-error/40 bg-error/10' };
    case 'DeploymentStarted':
      return { label: 'Deployment Triggered', variant: 'info', icon: Radio, color: 'text-brand-blue border-brand-blue/40 bg-brand-blue/10' };
    case 'DeploymentCompleted':
      return { label: 'Deployment Completed', variant: 'success', icon: CheckCircle2, color: 'text-success border-success/40 bg-success/10' };
    case 'RunCompleted':
      return { label: 'Run Completed', variant: 'success', icon: CheckCircle2, color: 'text-success border-success/40 bg-success/10' };
    case 'RunFailed':
      return { label: 'Run Failed', variant: 'danger', icon: XCircle, color: 'text-error border-error/40 bg-error/10' };
    case 'RunCancelled':
      return { label: 'Run Cancelled', variant: 'neutral', icon: XCircle, color: 'text-muted-foreground border-border bg-surface-raised' };
    default:
      return {
        label: eventType.replace(/([A-Z])/g, ' $1').trim(),
        variant: 'info',
        icon: Clock,
        color: 'text-brand-teal border-brand-teal/40 bg-brand-teal/10',
      };
  }
}

function renderPayloadSummary(event: DomainEventEnvelope): string | null {
  const p = event.payload;
  if (!p || typeof p !== 'object') return null;

  if (p.reason) return `Reason: ${p.reason}`;
  if (p.url) return `Target: ${p.url}`;
  if (p.prototype_ref) return `Reference: ${p.prototype_ref}`;
  if (p.commit_sha) return `Commit: ${String(p.commit_sha).substring(0, 7)}`;
  if (p.total_checks) return `${p.total_checks} verification checks passed`;
  if (p.approver) return `Authorized by ${p.approver}`;
  if (p.revision_number) return `Revision #${p.revision_number}`;
  if (p.provider) return `Provider: ${p.provider}`;

  return null;
}

export function RunTimeline({
  events,
  status,
  streamError,
  onReconnect,
  currentStage,
}: RunTimelineProps) {
  const listRef = React.useRef<HTMLDivElement>(null);

  // Auto scroll to bottom when new events arrive
  React.useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [events.length]);

  return (
    <div className="flex flex-col h-full rounded-xl border border-border bg-surface/80 backdrop-blur-sm overflow-hidden shadow-sm">
      {/* Header & Stream Status */}
      <div className="flex items-center justify-between px-3.5 py-2.5 border-b border-border bg-surface-raised/40">
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-brand-teal animate-pulse" />
          <span className="text-xs font-semibold text-foreground tracking-wider uppercase font-mono">
            Mission Timeline
          </span>
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-surface-raised border border-border text-muted-foreground">
            <AnimatedCounter value={events.length} />
          </span>
        </div>

        {/* Live SSE status indicator */}
        <div className="flex items-center gap-1.5">
          {status === 'connected' ? (
            <span className="inline-flex items-center gap-1.5 text-[11px] font-mono text-success">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-success" />
              </span>
              <span>LIVE</span>
            </span>
          ) : status === 'connecting' || status === 'reconnecting' ? (
            <span className="inline-flex items-center gap-1 text-[11px] font-mono text-warning">
              <RefreshCw className="h-3 w-3 animate-spin" />
              <span>SYNCING</span>
            </span>
          ) : (
            <div className="flex items-center gap-1.5">
              <span className="inline-flex items-center gap-1 text-[11px] font-mono text-muted-foreground">
                <WifiOff className="h-3 w-3" />
                <span>OFFLINE</span>
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="h-5 px-1.5 text-[10px] font-mono hover:text-brand-teal"
                onClick={onReconnect}
                title="Reconnect to event stream"
              >
                RECONNECT
              </Button>
            </div>
          )}
        </div>
      </div>

      {streamError && (
        <div className="px-3 py-1.5 bg-warning/10 border-b border-warning/20 text-[11px] text-warning flex items-center justify-between font-mono">
          <span className="truncate">{streamError}</span>
          <button
            type="button"
            onClick={onReconnect}
            className="underline font-semibold hover:opacity-80 shrink-0 ml-2"
          >
            Retry
          </button>
        </div>
      )}

      {/* Events List with Framer Motion AnimatePresence */}
      <div
        ref={listRef}
        className="flex-1 overflow-y-auto p-4 space-y-3 min-h-[340px] max-h-[580px] scroll-smooth"
      >
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-center text-muted-foreground text-xs p-4">
            <Clock className="h-6 w-6 mb-2 text-brand-teal/50 animate-pulse" />
            <span className="font-mono text-xs text-foreground/80">
              Awaiting pipeline telemetry...
            </span>
            <span className="text-[11px] font-mono text-muted-foreground mt-1">
              Active stage: <span className="text-brand-teal uppercase">{currentStage}</span>
            </span>
          </div>
        ) : (
          <div className="relative border-l border-border/80 ml-3.5 pl-4 space-y-4">
            <AnimatePresence initial={false}>
              {events.map((event, idx) => {
                const meta = getEventMeta(event.event_type);
                const summary = renderPayloadSummary(event);
                const Icon = meta.icon;
                const isLatest = idx === events.length - 1;

                return (
                  <motion.div
                    key={event.event_id || `evt-${idx}`}
                    initial={{ opacity: 0, x: -12, scale: 0.96 }}
                    animate={{ opacity: 1, x: 0, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                    className="relative group"
                  >
                    {/* Glowing timeline node dot */}
                    <div
                      className={`absolute -left-[23px] top-1 h-3.5 w-3.5 rounded-full border-2 border-surface flex items-center justify-center transition-transform group-hover:scale-125 ${
                        meta.color
                      } ${isLatest ? 'ring-2 ring-brand-teal/40 animate-pulse' : ''}`}
                    />

                    <div className="rounded-lg p-2.5 bg-surface-raised/40 hover:bg-surface-raised/80 border border-border/60 transition-all">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-1.5 min-w-0">
                          <Icon className="h-3.5 w-3.5 shrink-0 opacity-80" />
                          <span
                            className={`text-xs tracking-tight truncate ${
                              isLatest
                                ? 'text-foreground font-semibold'
                                : 'text-foreground/90 font-medium'
                            }`}
                          >
                            {isLatest ? (
                              <TextScramble text={meta.label} speed={25} />
                            ) : (
                              meta.label
                            )}
                          </span>
                        </div>
                        <time className="font-mono text-[10px] text-muted-foreground shrink-0 tabular-nums">
                          {formatTime(event.occurred_at)}
                        </time>
                      </div>

                      {summary && (
                        <p className="text-[11px] text-muted-foreground/90 mt-1 leading-snug font-mono bg-background/50 px-2 py-1 rounded border border-border/40">
                          {summary}
                        </p>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
}
