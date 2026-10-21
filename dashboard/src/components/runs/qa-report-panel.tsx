'use client';

import * as React from 'react';
import { CheckCircle2, XCircle, AlertCircle, ShieldAlert } from 'lucide-react';
import type { RunResponse } from '@/features/runs/types';

export interface QAReportPanelProps {
  run: RunResponse;
}

export function QAReportPanel({ run }: QAReportPanelProps) {
  const qa = run.qa_summary;
  const isFailed = run.status.toUpperCase() === 'FAILED' && run.failure_details?.reason?.includes('QA');

  if (!qa && !isFailed) {
    return (
      <div className="rounded border border-dashed border-border bg-surface/50 p-6 text-center text-xs text-muted-foreground">
        <CheckCircle2 className="h-6 w-6 mx-auto mb-2 opacity-40 text-muted-foreground" />
        <h4 className="font-medium text-foreground mb-1">QA Report Pending</h4>
        <p className="max-w-xs mx-auto text-[11px] leading-relaxed">
          Automated QA tests (Astro build compilation, internal link crawling, and axe-core accessibility audits) are executed after the code generation stage.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {isFailed && (
        <div
          role="alert"
          className="rounded border border-danger/30 bg-danger-surface p-3 text-xs text-danger flex items-start gap-2.5"
        >
          <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold block">Quality Assurance Failure</span>
            <span className="text-[11px] leading-relaxed block mt-0.5">
              {run.failure_details?.reason || 'One or more automated verification checks failed during the test phase.'}
            </span>
          </div>
        </div>
      )}

      {qa ? (
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-2">
            <div className="rounded border border-border bg-surface p-2.5 text-center">
              <span className="text-[10px] uppercase font-medium text-muted-foreground block">
                Total Checks
              </span>
              <span className="text-sm font-mono font-semibold text-foreground">
                {qa.total_checks ?? '—'}
              </span>
            </div>
            <div className="rounded border border-border bg-surface p-2.5 text-center">
              <span className="text-[10px] uppercase font-medium text-success block">
                Passed
              </span>
              <span className="text-sm font-mono font-semibold text-success">
                {qa.passed_checks ?? '—'}
              </span>
            </div>
            <div className="rounded border border-border bg-surface p-2.5 text-center">
              <span className="text-[10px] uppercase font-medium text-danger block">
                Failed
              </span>
              <span className="text-sm font-mono font-semibold text-danger">
                {qa.failed_checks?.length ?? 0}
              </span>
            </div>
          </div>

          {Array.isArray(qa.failed_checks) && qa.failed_checks.length > 0 && (
            <div className="rounded border border-danger/20 bg-surface p-3">
              <h5 className="text-[11px] font-semibold text-danger mb-1.5 uppercase tracking-wide">
                Failed Audit Checks
              </h5>
              <ul className="space-y-1 text-xs">
                {qa.failed_checks.map((fc: any, i: number) => (
                  <li key={i} className="flex items-center gap-1.5 text-danger font-mono text-[11px]">
                    <XCircle className="h-3 w-3 shrink-0" />
                    <span>{typeof fc === 'string' ? fc : JSON.stringify(fc)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : (
        <div className="rounded border border-border bg-surface p-3 text-xs text-muted-foreground font-mono">
          QA execution logged: {JSON.stringify(run.failure_details || {})}
        </div>
      )}
    </div>
  );
}
