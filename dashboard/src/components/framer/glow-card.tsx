'use client';

import * as React from 'react';
import { motion, useMotionTemplate, useMotionValue } from 'framer-motion';
import { cn } from '@/lib/utils';
import { hoverCardVariants } from '@/lib/motion';

export interface GlowCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  interactive?: boolean;
  glowColor?: string;
  badge?: React.ReactNode;
}

export function GlowCard({
  children,
  className,
  interactive = true,
  glowColor = 'rgba(84, 225, 193, 0.08)',
  badge,
  ...props
}: GlowCardProps) {
  const mouseX = useMotionValue(-1000);
  const mouseY = useMotionValue(-1000);

  function handleMouseMove({ currentTarget, clientX, clientY }: React.MouseEvent) {
    const { left, top } = currentTarget.getBoundingClientRect();
    mouseX.set(clientX - left);
    mouseY.set(clientY - top);
  }

  function handleMouseLeave() {
    mouseX.set(-1000);
    mouseY.set(-1000);
  }

  return (
    <motion.div
      onMouseMove={interactive ? handleMouseMove : undefined}
      onMouseLeave={interactive ? handleMouseLeave : undefined}
      variants={interactive ? hoverCardVariants : undefined}
      initial={interactive ? 'initial' : undefined}
      whileHover={interactive ? 'hover' : undefined}
      whileTap={interactive ? 'press' : undefined}
      className={cn(
        'group relative rounded-lg border border-border bg-surface text-foreground shadow-xs overflow-hidden transition-colors',
        interactive && 'hover:border-accent/40',
        className
      )}
      {...(props as any)}
    >
      {/* Subtle radial cursor spotlight */}
      {interactive && (
        <motion.div
          className="pointer-events-none absolute -inset-px rounded-lg opacity-0 transition-opacity duration-300 group-hover:opacity-100 -z-0"
          style={{
            background: useMotionTemplate`
              radial-gradient(
                350px circle at ${mouseX}px ${mouseY}px,
                ${glowColor},
                transparent 80%
              )
            `,
          }}
        />
      )}

      {badge && <div className="absolute top-3 right-3 z-10">{badge}</div>}

      <div className="relative z-10 h-full">{children}</div>
    </motion.div>
  );
}
