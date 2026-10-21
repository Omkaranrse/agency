'use client';

import * as React from 'react';
import { motion, type HTMLMotionProps } from 'framer-motion';
import { Slot } from '@radix-ui/react-slot';
import { cn } from '@/lib/utils';
import { tactileButtonVariants } from '@/lib/motion';

export interface ShimmerButtonProps extends Omit<HTMLMotionProps<'button'>, 'ref'> {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'outline' | 'danger';
  size?: 'sm' | 'default' | 'lg';
  isLoading?: boolean;
  shimmerColor?: string;
  asChild?: boolean;
}

export function ShimmerButton({
  children,
  className,
  variant = 'primary',
  size = 'default',
  isLoading = false,
  shimmerColor,
  asChild = false,
  disabled,
  ...props
}: ShimmerButtonProps) {
  const sizeClasses = {
    sm: 'h-8 px-3 text-xs',
    default: 'h-9 px-4 text-xs font-medium',
    lg: 'h-10 px-5 text-sm font-medium',
  }[size];

  const variantClasses = {
    primary:
      'bg-accent text-accent-foreground border-accent shadow-sm hover:bg-accent-hover font-semibold',
    secondary:
      'bg-surface-raised text-foreground border-border hover:bg-surface-raised/80',
    outline:
      'bg-transparent text-foreground border-border hover:bg-surface-raised hover:border-accent/40',
    danger:
      'bg-danger text-danger-foreground border-danger hover:opacity-90',
  }[variant];

  if (asChild) {
    return (
      <Slot
        className={cn(
          'group relative inline-flex items-center justify-center gap-2 rounded-md border select-none transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:pointer-events-none',
          sizeClasses,
          variantClasses,
          className
        )}
        {...(props as any)}
      >
        {children}
      </Slot>
    );
  }

  return (
    <motion.button
      variants={tactileButtonVariants}
      initial="initial"
      whileHover={disabled || isLoading ? undefined : 'hover'}
      whileTap={disabled || isLoading ? undefined : 'tap'}
      disabled={disabled || isLoading}
      className={cn(
        'group relative inline-flex items-center justify-center gap-2 rounded-md border select-none transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:pointer-events-none',
        sizeClasses,
        variantClasses,
        className
      )}
      {...props}
    >
      {/* Subtle edge shimmer line on hover for primary and outline */}
      {(variant === 'primary' || variant === 'outline' || shimmerColor) && (
        <span
          className="pointer-events-none absolute -inset-[1px] rounded-md opacity-0 transition-opacity duration-300 group-hover:opacity-100 overflow-hidden"
          aria-hidden="true"
        >
          <span
            className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full animate-[shimmer_2s_infinite]"
            style={shimmerColor ? { background: `linear-gradient(90deg, transparent, ${shimmerColor}40, transparent)` } : undefined}
          />
        </span>
      )}

      {isLoading ? (
        <span className="flex items-center gap-2">
          <svg
            className="h-3.5 w-3.5 animate-spin"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <span>Processing...</span>
        </span>
      ) : (
        children
      )}
    </motion.button>
  );
}
