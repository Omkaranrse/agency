import * as React from 'react';
import { cn } from '@/lib/utils';

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean;
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, error, disabled, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          'flex min-h-[80px] w-full rounded border border-border bg-surface px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50 resize-y',
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
Textarea.displayName = 'Textarea';

export { Textarea };
