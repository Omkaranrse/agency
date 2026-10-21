import * as React from 'react';
import { StatusBadge } from '@/components/ui/status-badge';

export interface RunStatusProps {
  status: string;
  stage?: string;
  revision?: number;
  className?: string;
}

export function RunStatusBadge({ status, stage, revision, className }: RunStatusProps) {
  return (
    <div className={`inline-flex items-center gap-1.5 ${className ?? ''}`}>
      <StatusBadge status={status} />
      {typeof revision === 'number' && revision > 0 && (
        <span
          className="text-[10px] font-mono border border-border bg-surface-raised px-1 py-0.5 rounded text-muted-foreground"
          title={`Revision ${revision}`}
        >
          r{revision}
        </span>
      )}
    </div>
  );
}
