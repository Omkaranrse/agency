import * as React from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface SelectProps
  extends React.SelectHTMLAttributes<HTMLSelectElement> {
  error?: boolean;
}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, error, disabled, ...props }, ref) => {
    return (
      <div className="relative w-full">
        <select
          className={cn(
            'flex h-8 w-full appearance-none rounded border border-border bg-surface px-3 pr-8 py-1 text-xs text-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer',
            error && 'border-danger focus-visible:ring-danger',
            className
          )}
          ref={ref}
          disabled={disabled}
          aria-invalid={error ? true : undefined}
          {...props}
        >
          {children}
        </select>
        <ChevronDown
          className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground"
          aria-hidden="true"
        />
      </div>
    );
  }
);
Select.displayName = 'Select';

export { Select };
