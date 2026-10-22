'use client';

import * as React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText,
  ShieldCheck,
  Cpu,
  Code2,
  FileCode,
  Copy,
  Check,
  Layers,
  Clock,
  AlertTriangle,
  Sparkles,
} from 'lucide-react';
import { SlidingTabs } from '@/components/framer/sliding-tabs';
import { AnimatedCounter } from '@/components/framer/animated-counter';
import { QAReportPanel } from './qa-report-panel';
import { useRunArtifacts } from '@/features/runs/queries';
import type { RunResponse, DomainEventEnvelope } from '@/features/runs/types';

export interface RunDetailsPanelProps {
  run: RunResponse;
  events: DomainEventEnvelope[];
}

export function RunDetailsPanel({ run, events }: RunDetailsPanelProps) {
  const [activeTab, setActiveTab] = React.useState<string>('overview');
  const [selectedArtifactId, setSelectedArtifactId] = React.useState<string | null>(null);
  const [copied, setCopied] = React.useState(false);

  const { data: artifactsData, isLoading: isArtifactsLoading } = useRunArtifacts(
    run.run_id
  );
  const artifacts = React.useMemo(() => artifactsData?.items || [], [artifactsData?.items]);

  const tabs = [
    { id: 'overview', label: 'Overview', icon: FileText },
    { id: 'artifacts', label: 'Code & Diffs', icon: FileCode },
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

          {activeTab === 'artifacts' && (
            <motion.div
              key="artifacts"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.18 }}
              className="space-y-3"
            >
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider font-mono">
                  Generated Artifacts
                </h4>
                <span className="text-[10px] font-mono text-accent px-1.5 py-0.5 rounded bg-accent/10 border border-accent/30">
                  {artifacts.length} {artifacts.length === 1 ? 'FILE' : 'FILES'}
                </span>
              </div>

              {isArtifactsLoading ? (
                <div className="space-y-2 py-4">
                  <div className="h-8 rounded bg-surface-raised animate-pulse" />
                  <div className="h-8 rounded bg-surface-raised animate-pulse" />
                  <div className="h-8 rounded bg-surface-raised animate-pulse" />
                </div>
              ) : artifacts.length === 0 ? (
                <div className="flex flex-col items-center justify-center p-6 text-center rounded-lg border border-border/80 bg-background/50 space-y-2">
                  <FileCode className="h-8 w-8 text-muted-foreground/60" />
                  <p className="text-xs font-medium text-foreground">No Code Artifacts Yet</p>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                    Builder and QA agents emit source files (HTML, React, CSS, config) as stages complete.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="divide-y divide-border/60 rounded-lg border border-border/80 bg-background/50 overflow-hidden">
                    {artifacts.map((art) => {
                      const isSelected = selectedArtifactId === art.artifact_id;
                      return (
                        <div
                          key={art.artifact_id}
                          onClick={() => setSelectedArtifactId(isSelected ? null : art.artifact_id)}
                          className={`p-2.5 flex items-center justify-between gap-2 cursor-pointer transition-colors ${
                            isSelected
                              ? 'bg-accent/10 border-l-2 border-l-accent'
                              : 'hover:bg-surface-raised/60'
                          }`}
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <FileCode className="h-4 w-4 shrink-0 text-accent" />
                            <div className="min-w-0">
                              <span className="font-mono text-xs text-foreground font-medium block truncate">
                                {art.display_name}
                              </span>
                              <span className="text-[10px] font-mono text-muted-foreground block">
                                {art.artifact_type} &bull;{' '}
                                {art.size_bytes ? `${Math.round(art.size_bytes / 1024)} KB` : 'Dynamic'}
                              </span>
                            </div>
                          </div>

                          <div className="flex items-center gap-1 shrink-0">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                navigator.clipboard.writeText(art.artifact_id);
                                setCopied(true);
                                setTimeout(() => setCopied(false), 2000);
                              }}
                              title="Copy artifact ID"
                              className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-surface-raised"
                            >
                              {copied ? (
                                <Check className="h-3 w-3 text-success" />
                              ) : (
                                <Copy className="h-3 w-3" />
                              )}
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {selectedArtifactId && (
                    <div className="p-3 rounded-lg border border-border/80 bg-surface-raised/40 space-y-1.5 font-mono text-[11px]">
                      <div className="flex justify-between items-center text-muted-foreground">
                        <span>Selected Artifact:</span>
                        <span className="text-accent truncate select-all">{selectedArtifactId}</span>
                      </div>
                      <div className="text-[10px] text-muted-foreground/80">
                        File ready for operator inspection or export via VCS pipeline.
                      </div>
                    </div>
                  )}
                </div>
              )}
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
                  <span className="text-foreground font-semibold">Groq (Llama 3.3 70B) / Gemini</span>
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
