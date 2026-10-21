import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import {
  Clock,
  Compass,
  AlertCircle,
  Hammer,
  CheckCircle2,
  XCircle,
  Ban,
  Rocket,
  Search,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { STATUS_DEFINITIONS, type RunStatus } from '@/lib/design-tokens';

const statusBadgeVariants = cva(
  'inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium border select-none transition-colors whitespace-nowrap',
  {
    variants: {
      variant: {
        neutral:
          'bg-surface-raised border-border text-foreground',
        info:
          'bg-accent/10 border-accent/25 text-accent dark:text-[#6CB3A8]',
        warning:
          'bg-warning-surface border-warning/30 text-warning dark:text-[#E29D86]',
        success:
          'bg-success-surface border-success/30 text-success dark:text-[#72B889]',
        danger:
          'bg-danger-surface border-danger/30 text-danger dark:text-[#CF7982]',
      },
      size: {
        default: 'text-[11px] px-2 py-0.5',
        sm: 'text-[10px] px-1.5 py-0.5',
        lg: 'text-xs px-2.5 py-1',
      },
    },
    defaultVariants: {
      variant: 'neutral',
      size: 'default',
    },
  }
);

export interface StatusBadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof statusBadgeVariants> {
  status: RunStatus | string;
  showIcon?: boolean;
}

function getStatusIcon(status: string) {
  switch (status.toLowerCase()) {
    case 'created':
      return Clock;
    case 'planning':
      return Compass;
    case 'awaiting_approval':
      return AlertCircle;
    case 'building':
      return Hammer;
    case 'testing':
      return Search;
    case 'deploying':
      return Rocket;
    case 'completed':
      return CheckCircle2;
    case 'failed':
      return XCircle;
    case 'cancelled':
      return Ban;
    default:
      return Clock;
  }
}

export function StatusBadge({
  status,
  showIcon = true,
  className,
  size,
  ...props
}: StatusBadgeProps) {
  const normalizedKey = status.toLowerCase() as RunStatus;
  const meta = STATUS_DEFINITIONS[normalizedKey] || {
    label: status.replace(/_/g, ' '),
    variant: 'neutral' as const,
    description: status,
  };

  const IconComponent = getStatusIcon(status);

  return (
    <span
      className={cn(statusBadgeVariants({ variant: meta.variant, size, className }))}
      role="status"
      title={meta.description}
      {...props}
    >
      {showIcon && (
        <IconComponent
          className="h-3 w-3 shrink-0"
          aria-hidden="true"
        />
      )}
      <span>{meta.label}</span>
    </span>
  );
}
