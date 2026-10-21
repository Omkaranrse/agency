'use client';

import * as React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText, ShieldCheck, Cpu, Code2, Layers, Clock, AlertTriangle, Sparkles } from 'lucide-react';
import { SlidingTabs } from '@/components/framer/sliding-tabs';
import { AnimatedCounter } from '@/components/framer/animated-counter';
import { QAReportPanel } from './qa-report-panel';
import type { RunResponse, DomainEventEnvelope } from '@/features/runs/types';

export interface RunDetailsPanelProps {
  run: RunResponse;
  events: DomainEventEnvelope[];
}

export function RunDetailsPanel({ run, events }: RunDetailsPanelProps) {
  const [activeTab, setActiveTab] = React.useState<string>('overview');

  const tabs = [
    { id: 'overview', label: 'Overview', icon: FileText },
    { id: 'qa', label: 'QA Report', icon: ShieldCheck },
    { id: 'usage', label: 'Telemetry', icon: Cpu },
    { id: 'raw', label: 'Raw Log', icon: Code2 },
  ];

  return (
    <div className="flex flex-col h-full rounded-xl border border-border bg-surface/80 backdrop-blur-sm overflow-hidden shadow-sm">
      {/* Sliding Tabs Header */}
      <div className="p-2 border-b border-border bg-surface-raised/40">
        <SlidingTabs
          tabs={tabs}
          activeTab={activeTab}
          onChange={setActiveTab}
          className="w-full"
        />
      </div>

      {/* Tab Body */}
      <div className="flex-1 p-4 overflow-y-auto min-h-[340px] max-h-[580px] text-xs">
        <AnimatePresence mode="wait">
          {activeTab === 'overview' && (
            <motion.div
              key="overview"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.18 }}
              className="space-y-4"
            >
              {/* Run Identifier Card */}
              <div className="p-3 rounded-lg border border-border/80 bg-background/50 space-y-1">
                <span className="text-[10px] font-mono font-medium text-muted-foreground uppercase tracking-wider block">
                  Run Identifier
                </span>
                <span className="font-mono text-xs text-brand-teal select-all block truncate">
                  {run.run_id}
                </span>
              </div>

              {/* Project Name Card */}
              <div className="p-3 rounded-lg border border-border/80 bg-background/50 space-y-1">
                <span className="text-[10px] font-mono font-medium text-muted-foreground uppercase tracking-wider block">
                  Project Workspace
                </span>
                <span className="font-semibold text-foreground text-sm block">
                  {run.project_id}
                </span>
              </div>

              {/* Stage & Revision Grid */}
              <div className="grid grid-cols-2 gap-2.5">
                <div className="rounded-lg border border-border/80 bg-surface-raised/60 p-3">
                  <span className="text-[10px] font-mono uppercase text-muted-foreground block">
                    Pipeline Stage
                  </span>
                  <span className="font-semibold text-foreground capitalize mt-1 block tracking-wide">
                    {run.current_stage.replace(/_/g, ' ')}
                  </span>
                </div>

                <div className="rounded-lg border border-border/80 bg-surface-raised/60 p-3">
                  <span className="text-[10px] font-mono uppercase text-muted-foreground block">
                    Revision Iteration
                  </span>
                  <span className="font-mono text-foreground font-semibold mt-1 block flex items-center gap-1">
                    #<AnimatedCounter value={run.current_revision ?? 0} />
                  </span>
                </div>
              </div>

              {/* Failure Details */}
              {run.failure_details?.reason && (
                <div className="rounded-lg border border-error/40 bg-error/10 p-3 text-error">
                  <div className="flex items-center gap-1.5 font-semibold text-[11px] uppercase tracking-wide">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    <span>Failure Reason</span>
                  </div>
                  <p className="mt-1 text-xs font-mono text-error/90 leading-relaxed">
                    {run.failure_details.reason}
                  </p>
                </div>
              )}

              {/* Timestamps */}
              <div className="pt-2 text-[11px] text-muted-foreground space-y-1.5 border-t border-border/80 font-mono">
                <div className="flex justify-between items-center">
                  <span>Initialized:</span>
                  <span className="text-foreground">{new Date(run.created_at).toLocaleString()}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span>Synchronized:</span>
                  <span className="text-foreground">{new Date(run.updated_at).toLocaleString()}</span>
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'qa' && (
            <motion.div
              key="qa"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.18 }}
            >
              <QAReportPanel run={run} />
            </motion.div>
          )}

          {activeTab === 'usage' && (
            <motion.div
              key="usage"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.18 }}
              className="space-y-3"
            >
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider font-mono">
                  Agent Telemetry
                </h4>
                <span className="text-[10px] font-mono text-brand-teal px-1.5 py-0.5 rounded bg-brand-teal/10 border border-brand-teal/30">
                  REAL-TIME
                </span>
              </div>
              <p className="text-muted-foreground leading-relaxed text-xs">
                Resource quotas and token telemetry across Project Manager, Designer, and Builder subagents are tracked deterministically.
              </p>

              <div className="rounded-lg border border-border/80 bg-background/50 p-3 space-y-2.5 font-mono text-[11px]">
                <div className="flex justify-between items-center pb-2 border-b border-border/50">
                  <span className="text-muted-foreground">Primary Intelligence:</span>
                  <span className="text-foreground font-semibold">Gemini 2.5 Flash</span>
                </div>
                <div className="flex justify-between items-center pb-2 border-b border-border/50">
                  <span className="text-muted-foreground">Deterministic Fallback:</span>
                  <span className="text-foreground">Ollama Local</span>
                </div>
                <div className="flex justify-between items-center pb-2 border-b border-border/50">
                  <span className="text-muted-foreground">Runtime Isolation:</span>
                  <span className="text-brand-blue">Docker Sandbox</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Strict Guardrails:</span>
                  <span className="text-success font-semibold flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" />
                    Enforced (Bounded)
                  </span>
                </div>
              </div>
            </motion.div>
          )}

          {activeTab === 'raw' && (
            <motion.div
              key="raw"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.18 }}
              className="space-y-2"
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono text-muted-foreground">
                  Stream Buffer: <span className="text-foreground font-semibold">{events.length}</span> frames
                </span>
              </div>
              <pre className="rounded-lg bg-background/80 p-3 text-[10px] font-mono overflow-auto max-h-[420px] border border-border/80 text-foreground leading-relaxed">
                {events.length === 0
                  ? '// Awaiting domain events payload...'
                  : JSON.stringify(events, null, 2)}
              </pre>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
