import * as React from 'react';
import { cn } from '@/lib/utils';

export interface PageHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  description?: string;
  breadcrumbs?: React.ReactNode;
  actions?: React.ReactNode;
}

export function PageHeader({
  title,
  description,
  breadcrumbs,
  actions,
  className,
  ...props
}: PageHeaderProps) {
  return (
    <div
      className={cn(
        'flex flex-col gap-3 pb-5 mb-5 border-b border-border sm:flex-row sm:items-start sm:justify-between',
        className
      )}
      {...props}
    >
      <div className="space-y-1 min-w-0">
        {breadcrumbs && <div className="mb-1.5">{breadcrumbs}</div>}
        <h1 className="text-xl font-semibold tracking-tight text-foreground truncate">
          {title}
        </h1>
        {description && (
          <p className="text-xs text-muted-foreground max-w-2xl leading-normal">
            {description}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex items-center gap-2 shrink-0 pt-1 sm:pt-0">
          {actions}
        </div>
      )}
    </div>
  );
}
