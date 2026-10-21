import * as React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './button';
import { cn } from '@/lib/utils';

export interface ErrorStateProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  message: string;
  referenceId?: string;
  onRetry?: () => void;
  isRetrying?: boolean;
}

export function ErrorState({
  title = 'Something went wrong',
  message,
  referenceId,
  onRetry,
  isRetrying = false,
  className,
  ...props
}: ErrorStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center p-8 text-center rounded border border-danger/30 bg-danger-surface/40 min-h-[220px]',
        className
      )}
      role="alert"
      aria-live="assertive"
      {...props}
    >
      <div className="flex h-10 w-10 items-center justify-center rounded bg-danger-surface border border-danger/20 text-danger mb-3">
        <AlertTriangle className="h-5 w-5" aria-hidden="true" />
      </div>
      <h3 className="text-sm font-medium text-danger dark:text-[#CF7982] tracking-tight mb-1">
        {title}
      </h3>
      <p className="text-xs text-foreground/80 max-w-md mb-3 leading-relaxed">
        {message}
      </p>

      {referenceId && (
        <p className="text-[11px] font-mono text-muted-foreground mb-4 select-all">
          Ref: {referenceId}
        </p>
      )}

      {onRetry && (
        <Button
          variant="outline"
          size="sm"
          onClick={onRetry}
          isLoading={isRetrying}
          className="border-danger/30 hover:bg-danger-surface"
        >
          <RefreshCw className="h-3 w-3 mr-1" aria-hidden="true" />
          <span>Retry</span>
        </Button>
      )}
    </div>
  );
}
