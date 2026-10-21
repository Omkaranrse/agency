import * as React from 'react';
import { LucideIcon, Inbox } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  description?: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
}

export function EmptyState({
  title,
  description,
  icon: Icon = Inbox,
  action,
  className,
  ...props
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center p-8 text-center rounded border border-dashed border-border bg-surface/50 min-h-[220px]',
        className
      )}
      role="region"
      aria-label={title}
      {...props}
    >
      <div className="flex h-10 w-10 items-center justify-center rounded bg-surface-raised text-muted-foreground mb-3">
        <Icon className="h-5 w-5" aria-hidden="true" />
      </div>
      <h3 className="text-sm font-medium text-foreground tracking-tight mb-1">
        {title}
      </h3>
      {description && (
        <p className="text-xs text-muted-foreground max-w-sm mb-4 leading-relaxed">
          {description}
        </p>
      )}
      {action && <div className="mt-1">{action}</div>}
    </div>
  );
}
