'use client';

import * as React from 'react';
import { Check, Edit3, X, AlertTriangle, ShieldCheck, Sparkles, Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';
import { ShimmerButton } from '@/components/framer/shimmer-button';
import { TextScramble } from '@/components/framer/text-scramble';
import { GlowCard } from '@/components/framer/glow-card';
import { useApproveRun, useReviseRun, useCancelRun } from '@/features/runs/mutations';
import { parseApiError } from '@/lib/api/config';
import type { RunResponse } from '@/features/runs/types';

export interface ApprovalPanelProps {
  run: RunResponse;
  onRefreshRun: () => void;
}

export function ApprovalPanel({ run, onRefreshRun }: ApprovalPanelProps) {
  const [mode, setMode] = React.useState<'idle' | 'revise'>('idle');
  const [comment, setComment] = React.useState('');
  const [commentError, setCommentError] = React.useState<string | null>(null);
  const [confirmCancelOpen, setConfirmCancelOpen] = React.useState(false);
  const [actionError, setActionError] = React.useState<string | null>(null);

  const approveMutation = useApproveRun(run.run_id);
  const reviseMutation = useReviseRun(run.run_id);
  const cancelMutation = useCancelRun(run.run_id);

  const isSubmitting =
    approveMutation.isPending || reviseMutation.isPending || cancelMutation.isPending;

  const currentRevision = run.current_revision ?? 0;
  const maxRevisions = 3;
  const revisionsRemaining = Math.max(0, maxRevisions - currentRevision);

  const handleApprove = async () => {
    setActionError(null);
    try {
      await approveMutation.mutateAsync({
        revision: currentRevision,
        approver: 'operator',
      });
      onRefreshRun();
    } catch (err) {
      const parsed = parseApiError(err);
      setActionError(parsed.message);
      if (parsed.status === 409) {
        onRefreshRun();
      }
    }
  };

  const handleReviseSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionError(null);

    const cleanComment = comment.trim();
    if (!cleanComment) {
      setCommentError('Please provide specific, actionable feedback for the revision.');
      return;
    }
    if (cleanComment.length > 1000) {
      setCommentError('Feedback must be 1000 characters or fewer.');
      return;
    }

    setCommentError(null);
    try {
      await reviseMutation.mutateAsync({
        revision: currentRevision,
        comment: cleanComment,
      });
      setComment('');
      setMode('idle');
      onRefreshRun();
    } catch (err) {
      const parsed = parseApiError(err);
      setActionError(parsed.message);
      if (parsed.status === 409) {
        onRefreshRun();
      }
    }
  };

  const handleCancelRun = async () => {
    try {
      await cancelMutation.mutateAsync({
        reason: 'Cancelled by operator during prototype review gate',
      });
      setConfirmCancelOpen(false);
      onRefreshRun();
    } catch (err) {
      const parsed = parseApiError(err);
      setActionError(parsed.message);
    }
  };

  return (
    <GlowCard
      glowColor="rgba(244, 188, 98, 0.15)"
      className="border-warning/40 bg-warning/5 backdrop-blur-md p-5 space-y-4"
    >
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-warning/20 pb-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-warning/20 border border-warning/40 text-warning shadow-sm">
            <ShieldCheck className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-foreground uppercase tracking-widest font-mono flex items-center gap-2">
              <TextScramble text="Operator Approval Gate" />
              <span className="px-1.5 py-0.2 rounded text-[10px] bg-warning/20 text-warning border border-warning/30">
                ACTION REQUIRED
              </span>
            </h3>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Review prototype preview. Operator authorization is required to proceed to code build, automated QA, and deployment.
            </p>
          </div>
        </div>

        {/* Revision count badge */}
        <div className="flex items-center gap-2 text-xs">
          <span className="text-[11px] font-mono text-muted-foreground px-2 py-1 rounded bg-background/60 border border-border">
            Iteration: <strong className="text-foreground">#{currentRevision}</strong> ({revisionsRemaining} remaining)
          </span>
        </div>
      </div>

      {/* Action error display */}
      {actionError && (
        <div
          role="alert"
          className="rounded-lg border border-error/40 bg-error/10 p-3 text-xs text-error flex items-start gap-2.5 font-mono"
        >
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-semibold">Action Failed:</span> {actionError}
          </div>
        </div>
      )}

      {/* Mode Idle: Approve, Request Changes, Cancel buttons */}
      {mode === 'idle' ? (
        <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
          <div className="flex items-center gap-2.5">
            <ShimmerButton
              shimmerColor="#48C78E"
              isLoading={approveMutation.isPending}
              disabled={isSubmitting}
              onClick={handleApprove}
              className="bg-success text-success-foreground hover:bg-success/90 font-medium"
            >
              <Check className="h-4 w-4 mr-1.5" />
              <span>Approve & Advance Pipeline</span>
            </ShimmerButton>

            <Button
              variant="outline"
              size="sm"
              disabled={isSubmitting || revisionsRemaining === 0}
              onClick={() => setMode('revise')}
              className="border-warning/40 text-foreground hover:bg-warning/10"
              title={
                revisionsRemaining === 0
                  ? 'Maximum 3 revisions already utilized'
                  : 'Request specific modifications'
              }
            >
              <Edit3 className="h-3.5 w-3.5 mr-1.5 text-warning" />
              <span>Request Iteration</span>
            </Button>
          </div>

          <Button
            variant="ghost"
            size="sm"
            disabled={isSubmitting}
            onClick={() => setConfirmCancelOpen(true)}
            className="text-error hover:text-error hover:bg-error/10 text-xs font-mono"
          >
            <X className="h-3.5 w-3.5 mr-1" />
            <span>Abort Run</span>
          </Button>
        </div>
      ) : (
        /* Mode Revise: Feedback form */
        <form onSubmit={handleReviseSubmit} className="space-y-3 pt-1">
          <div className="space-y-1.5">
            <label htmlFor="revision-comment" className="block text-xs font-medium text-foreground">
              Revision Directives & Specification Adjustments <span className="text-error">*</span>
            </label>
            <p className="text-[11px] text-muted-foreground">
              State specific styling, copy, or structural modifications. The Designer and Builder agents will adjust the implementation accordingly.
            </p>
            <Textarea
              id="revision-comment"
              rows={3}
              placeholder="e.g., Adjust header typography contrast, replace hero CTA with secondary accent, format services into 3-column card grid..."
              value={comment}
              onChange={(e) => {
                setComment(e.target.value);
                if (commentError) setCommentError(null);
              }}
              error={Boolean(commentError)}
              disabled={isSubmitting}
              className="bg-background/80"
            />
            {commentError && (
              <p className="text-[11px] text-error font-mono">{commentError}</p>
            )}
          </div>

          <div className="flex items-center justify-end gap-2.5 pt-1">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={isSubmitting}
              onClick={() => {
                setMode('idle');
                setComment('');
                setCommentError(null);
              }}
            >
              Cancel
            </Button>
            <ShimmerButton
              type="submit"
              shimmerColor="#54E1C1"
              isLoading={reviseMutation.isPending}
              disabled={isSubmitting}
              className="bg-primary text-primary-foreground"
            >
              <Send className="h-3.5 w-3.5 mr-1.5" />
              <span>Dispatch Revision</span>
            </ShimmerButton>
          </div>
        </form>
      )}

      {/* Confirmation Dialog for Cancel */}
      <ConfirmDialog
        open={confirmCancelOpen}
        onOpenChange={setConfirmCancelOpen}
        title="Abort Generation Mission?"
        description="Are you certain you wish to terminate this run? Active sandbox execution will be halted immediately and no further revisions will be accepted."
        confirmLabel="Abort Run"
        cancelLabel="Continue Review"
        isDestructive
        isLoading={cancelMutation.isPending}
        onConfirm={handleCancelRun}
      />
    </GlowCard>
  );
}
