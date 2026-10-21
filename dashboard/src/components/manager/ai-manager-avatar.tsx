'use client';

import * as React from 'react';
import Image from 'next/image';
import { motion, useReducedMotion } from 'framer-motion';
import {
  Sparkles,
  Mic,
  Volume2,
  AlertCircle,
  CheckCircle2,
  AlertTriangle,
  Bot,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export type AvatarSize = 'xs' | 'sm' | 'md' | 'lg' | 'hero';
export type AvatarState =
  | 'idle'
  | 'listening'
  | 'thinking'
  | 'speaking'
  | 'success'
  | 'warning'
  | 'error';

export interface AIManagerAvatarProps {
  size?: AvatarSize;
  state?: AvatarState;
  showBadge?: boolean;
  showGlow?: boolean;
  className?: string;
  alt?: string;
}

const SIZE_CONFIG: Record<
  AvatarSize,
  {
    containerSize: string;
    px: number;
    badgeSize: string;
    iconSize: string;
    isHero?: boolean;
  }
> = {
  xs: { containerSize: 'h-6 w-6', px: 24, badgeSize: 'h-2 w-2', iconSize: 'h-2 w-2' },
  sm: { containerSize: 'h-8 w-8', px: 32, badgeSize: 'h-2.5 w-2.5', iconSize: 'h-2.5 w-2.5' },
  md: { containerSize: 'h-10 w-10', px: 40, badgeSize: 'h-3.5 w-3.5', iconSize: 'h-2.5 w-2.5' },
  lg: { containerSize: 'h-14 w-14', px: 56, badgeSize: 'h-4 w-4', iconSize: 'h-3 w-3' },
  hero: { containerSize: 'h-48 w-40 sm:h-64 sm:w-52', px: 260, badgeSize: 'h-6 w-6', iconSize: 'h-3.5 w-3.5', isHero: true },
};

export function AIManagerAvatar({
  size = 'md',
  state = 'idle',
  showBadge = true,
  showGlow = false,
  className,
  alt = 'AI Agency Manager — Confident Business Cat Mascot',
}: AIManagerAvatarProps) {
  const shouldReduceMotion = useReducedMotion();
  const config = SIZE_CONFIG[size] || SIZE_CONFIG.md;

  // Animation variants based on state
  const getMotionAnimation = () => {
    if (shouldReduceMotion) return {};

    switch (state) {
      case 'speaking':
        return {
          y: [0, -3, 0, -2, 0],
          scale: [1, 1.02, 1, 1.015, 1],
          transition: {
            duration: 1.2,
            repeat: Infinity,
            ease: 'easeInOut' as const,
          },
        };
      case 'thinking':
        return {
          rotate: [0, -1.5, 1.5, 0],
          y: [0, -2, 0],
          transition: {
            duration: 2.2,
            repeat: Infinity,
            ease: 'easeInOut' as const,
          },
        };
      case 'listening':
        return {
          scale: [1, 1.03, 1],
          transition: {
            duration: 1.4,
            repeat: Infinity,
            ease: 'easeInOut' as const,
          },
        };
      case 'success':
        return {
          y: [0, -6, 0],
          scale: [1, 1.04, 1],
          transition: {
            duration: 0.6,
            ease: 'easeOut' as const,
          },
        };
      case 'error':
        return {
          x: [0, -2, 2, -2, 2, 0],
          transition: {
            duration: 0.4,
            ease: 'easeInOut' as const,
          },
        };
      case 'warning':
        return {
          y: [0, -2, 0],
          transition: {
            duration: 1.8,
            repeat: Infinity,
            ease: 'easeInOut' as const,
          },
        };
      case 'idle':
      default:
        return {
          y: [0, -2, 0],
          transition: {
            duration: 3.5,
            repeat: Infinity,
            ease: 'easeInOut' as const,
          },
        };
    }
  };

  // State badge indicator
  const renderBadge = () => {
    if (!showBadge) return null;

    if (config.isHero) {
      return (
        <div
          className={cn(
            'absolute bottom-1 right-2 px-2 py-0.5 rounded-full border shadow-sm flex items-center gap-1.5 text-[10px] font-mono select-none backdrop-blur-md',
            state === 'speaking' && 'bg-accent/20 border-accent text-accent',
            state === 'listening' && 'bg-blue-500/20 border-blue-400 text-blue-400 animate-pulse',
            state === 'thinking' && 'bg-violet-500/20 border-violet-400 text-violet-400',
            state === 'success' && 'bg-success/20 border-success text-success',
            state === 'warning' && 'bg-warning/20 border-warning text-warning',
            state === 'error' && 'bg-danger/20 border-danger text-danger',
            state === 'idle' && 'bg-surface-raised/80 border-border text-muted-foreground'
          )}
        >
          {state === 'speaking' && <Volume2 className="h-3 w-3" />}
          {state === 'listening' && <Mic className="h-3 w-3" />}
          {state === 'thinking' && <Sparkles className="h-3 w-3 animate-spin" />}
          {state === 'success' && <CheckCircle2 className="h-3 w-3" />}
          {state === 'warning' && <AlertTriangle className="h-3 w-3" />}
          {state === 'error' && <AlertCircle className="h-3 w-3" />}
          {state === 'idle' && <span className="h-1.5 w-1.5 rounded-full bg-success" />}
          <span className="capitalize font-semibold">{state}</span>
        </div>
      );
    }

    return (
      <span
        className={cn(
          'absolute -bottom-0.5 -right-0.5 rounded-full border-2 border-surface flex items-center justify-center',
          config.badgeSize,
          state === 'speaking' && 'bg-accent text-accent-foreground',
          state === 'listening' && 'bg-blue-500 text-white animate-pulse',
          state === 'thinking' && 'bg-violet-500 text-white',
          state === 'success' && 'bg-success text-white',
          state === 'warning' && 'bg-warning text-black',
          state === 'error' && 'bg-danger text-white',
          state === 'idle' && 'bg-success text-white'
        )}
        title={`Status: ${state}`}
      >
        {size === 'lg' && (
          <>
            {state === 'speaking' && <Volume2 className={config.iconSize} />}
            {state === 'listening' && <Mic className={config.iconSize} />}
            {state === 'thinking' && <Sparkles className={config.iconSize} />}
          </>
        )}
      </span>
    );
  };

  // HERO (Full-body mascot) Presentation
  if (config.isHero) {
    return (
      <div className={cn('relative inline-flex flex-col items-center select-none', className)}>
        {/* Glow ambient background if enabled */}
        {showGlow && (
          <div
            className={cn(
              'absolute inset-0 rounded-full blur-2xl opacity-20 -z-10 transition-colors',
              state === 'speaking' && 'bg-accent',
              state === 'thinking' && 'bg-violet-500',
              state === 'listening' && 'bg-blue-400',
              state === 'idle' && 'bg-accent/40'
            )}
          />
        )}

        <motion.div
          animate={getMotionAnimation()}
          className="relative flex items-center justify-center"
        >
          <Image
            src="/ai-manager-cat.png"
            alt={alt}
            width={config.px}
            height={Math.round(config.px * 1.2)}
            priority
            className="drop-shadow-xl object-contain"
          />
        </motion.div>

        {renderBadge()}
      </div>
    );
  }

  // HEADSHOT (Compact, Standard, Large Avatars)
  return (
    <div className={cn('relative inline-block shrink-0 select-none', className)}>
      <motion.div
        animate={getMotionAnimation()}
        className={cn(
          'relative rounded-full overflow-hidden border transition-all flex items-center justify-center bg-surface-raised',
          config.containerSize,
          state === 'speaking' && 'border-accent shadow-xs ring-2 ring-accent/20',
          state === 'listening' && 'border-blue-400 shadow-xs ring-2 ring-blue-400/20',
          state === 'thinking' && 'border-violet-400 ring-2 ring-violet-400/20',
          state === 'idle' && 'border-border/80 hover:border-accent/40',
          state === 'warning' && 'border-warning ring-2 ring-warning/20',
          state === 'error' && 'border-danger ring-2 ring-danger/20'
        )}
      >
        <Image
          src="/ai-manager-cat.png"
          alt={alt}
          width={config.px * 1.5}
          height={Math.round(config.px * 1.8)}
          className="object-cover object-top scale-150 translate-y-1.5"
          priority={size === 'lg'}
        />
      </motion.div>

      {renderBadge()}
    </div>
  );
}
