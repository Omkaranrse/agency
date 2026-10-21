import * as React from 'react';
import { cn } from '@/lib/utils';

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, error, disabled, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          'flex h-8 w-full rounded border border-border bg-surface px-3 py-1 text-xs text-foreground placeholder:text-muted-foreground transition-colors file:border-0 file:bg-transparent file:text-xs file:font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50',
          error && 'border-danger focus-visible:ring-danger',
          className
        )}
        ref={ref}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        {...props}
      />
    );
  }
);
Input.displayName = 'Input';

export { Input };
