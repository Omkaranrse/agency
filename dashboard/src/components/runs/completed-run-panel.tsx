'use client';

import * as React from 'react';
import {
  CheckCircle2,
  ExternalLink,
  Download,
  FileText,
  GitBranch,
  Layers,
  AlertCircle,
  FileCheck,
  Sparkles,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { GlowCard } from '@/components/framer/glow-card';
import { ShimmerButton } from '@/components/framer/shimmer-button';
import { useRunArtifacts } from '@/features/runs/queries';
import { downloadArtifact } from '@/features/runs/api';
import type { RunResponse, ArtifactMetadataDTO } from '@/features/runs/types';

export interface CompletedRunPanelProps {
  run: RunResponse;
}

export function CompletedRunPanel({ run }: CompletedRunPanelProps) {
  const { data: artifactsData, isLoading: artifactsLoading, error: artifactsError } =
    useRunArtifacts(run.run_id);

  const [downloadingId, setDownloadingId] = React.useState<string | null>(null);
  const [downloadError, setDownloadError] = React.useState<string | null>(null);

  const productionUrl = run.production_url || run.preview_url;

  // Validate URL format
  const isValidProdUrl = React.useMemo(() => {
    if (!productionUrl) return false;
    try {
      const parsed = new URL(productionUrl);
      return parsed.protocol === 'http:' || parsed.protocol === 'https:';
    } catch {
      return false;
    }
  }, [productionUrl]);

  const handleDownload = async (artifact: ArtifactMetadataDTO) => {
    setDownloadingId(artifact.artifact_id);
    setDownloadError(null);
    try {
      await downloadArtifact(run.run_id, artifact.artifact_id, artifact.display_name);
    } catch (err: any) {
      setDownloadError(err?.message || 'Failed to download artifact file.');
    } finally {
      setDownloadingId(null);
    }
  };

  const artifacts = artifactsData?.items ?? [];

  return (
    <GlowCard
      glowColor="rgba(84, 225, 193, 0.12)"
      className="border-success/40 bg-success/5 backdrop-blur-md p-5 space-y-5"
    >
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-success/20 pb-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-success/20 border border-success/40 text-success shadow-sm">
            <CheckCircle2 className="h-6 w-6" aria-hidden="true" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-foreground tracking-tight">
                Mission Execution Successful
              </h3>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-success/20 text-success border border-success/30">
                DEPLOYED
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              Production compilation passed QA accessibility and performance checks and is deployed.
            </p>
          </div>
        </div>

        {isValidProdUrl && (
          <ShimmerButton
            asChild
            shimmerColor="#54E1C1"
            size="sm"
            className="bg-success text-success-foreground hover:bg-success/90"
          >
            <a
              href={productionUrl!}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5"
            >
              <span>Visit Production Site</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </ShimmerButton>
        )}
      </div>

      {/* Deployment & Repository Links */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
        <div className="rounded-lg border border-border/80 bg-background/60 p-3 space-y-1">
          <span className="text-[10px] font-mono font-medium text-muted-foreground uppercase tracking-wider block">
            Live Production Endpoint
          </span>
          {isValidProdUrl ? (
            <a
              href={productionUrl!}
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-brand-teal hover:underline flex items-center gap-1.5 truncate"
            >
              <span className="truncate">{productionUrl}</span>
              <ExternalLink className="h-3 w-3 shrink-0" />
            </a>
          ) : (
            <span className="text-muted-foreground font-mono text-[11px]">
              Internal preview active
            </span>
          )}
        </div>

        <div className="rounded-lg border border-border/80 bg-background/60 p-3 space-y-1">
          <span className="text-[10px] font-mono font-medium text-muted-foreground uppercase tracking-wider block">
            Version Control Target
          </span>
          <div className="flex items-center gap-1.5 font-mono text-muted-foreground">
            <GitBranch className="h-3.5 w-3.5 shrink-0 text-brand-blue" />
            <span className="truncate text-foreground">
              {run.build_summary?.repo || `agency/${run.project_id}`}
            </span>
          </div>
        </div>
      </div>

      {downloadError && (
        <div
          role="alert"
          className="rounded-lg border border-error/40 bg-error/10 p-2.5 text-xs text-error flex items-center gap-2 font-mono"
        >
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{downloadError}</span>
        </div>
      )}

      {/* Handover Artifacts */}
      <div className="space-y-2 pt-1">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider font-mono">
            Handover Artifacts Registry
          </h4>
          <span className="text-[11px] font-mono text-muted-foreground px-1.5 py-0.5 rounded bg-background/50 border border-border">
            {artifacts.length} file{artifacts.length === 1 ? '' : 's'}
          </span>
        </div>

        {artifactsLoading ? (
          <div className="p-4 text-center text-xs text-muted-foreground font-mono">
            Loading artifact registry...
          </div>
        ) : artifacts.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border/80 bg-background/40 p-4 text-center text-xs text-muted-foreground">
            <FileText className="h-5 w-5 mx-auto mb-1.5 opacity-40" />
            <span>No downloadable artifacts registered for this run.</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {artifacts.map((art) => (
              <div
                key={art.artifact_id}
                className="flex items-center justify-between p-3 rounded-lg border border-border/80 bg-background/60 hover:bg-background/90 transition-colors"
              >
                <div className="flex items-center gap-2.5 min-w-0 pr-2">
                  <FileCheck className="h-4 w-4 text-brand-teal shrink-0" />
                  <div className="truncate">
                    <span className="text-xs font-medium text-foreground block truncate">
                      {art.display_name}
                    </span>
                    <span className="text-[10px] font-mono text-muted-foreground">
                      {art.artifact_type}
                      {typeof art.size_bytes === 'number' && ` • ${(art.size_bytes / 1024).toFixed(1)} KB`}
                    </span>
                  </div>
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs font-mono shrink-0 hover:border-brand-teal hover:text-brand-teal"
                  isLoading={downloadingId === art.artifact_id}
                  disabled={!art.download_available || Boolean(downloadingId)}
                  onClick={() => handleDownload(art)}
                >
                  <Download className="h-3 w-3 mr-1" />
                  <span>Download</span>
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>
    </GlowCard>
  );
}
