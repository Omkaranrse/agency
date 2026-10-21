import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 disabled:pointer-events-none disabled:opacity-50 select-none text-xs',
  {
    variants: {
      variant: {
        primary:
          'bg-accent text-accent-foreground hover:bg-accent-hover active:bg-accent-hover shadow-none',
        secondary:
          'bg-surface-raised text-foreground hover:bg-border/60 border border-border shadow-none',
        outline:
          'border border-border bg-transparent text-foreground hover:bg-surface-raised active:bg-border/40 shadow-none',
        ghost:
          'bg-transparent text-foreground hover:bg-surface-raised active:bg-border/40 shadow-none',
        destructive:
          'bg-danger text-danger-foreground hover:opacity-90 active:opacity-100 shadow-none',
      },
      size: {
        default: 'h-8 px-3.5 gap-1.5',
        sm: 'h-7 px-2.5 text-[11px] gap-1',
        lg: 'h-9 px-4 text-sm gap-2',
        icon: 'h-8 w-8 p-0',
        'icon-sm': 'h-7 w-7 p-0',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  isLoading?: boolean;
  loadingText?: string;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      asChild = false,
      isLoading = false,
      loadingText,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    if (asChild) {
      return (
        <Slot
          className={cn(buttonVariants({ variant, size, className }))}
          ref={ref}
          {...props}
        >
          {children}
        </Slot>
      );
    }

    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || isLoading}
        aria-busy={isLoading ? true : undefined}
        {...props}
      >
        {isLoading ? (
          <>
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
            <span>{loadingText || children}</span>
          </>
        ) : (
          children
        )}
      </button>
    );
  }
);
Button.displayName = 'Button';

export { Button, buttonVariants };
