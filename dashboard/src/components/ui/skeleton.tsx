import * as React from 'react';
import { cn } from '@/lib/utils';

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {}

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse rounded bg-surface-raised/80 motion-reduce:animate-none',
        className
      )}
      aria-hidden="true"
      {...props}
    />
  );
}
