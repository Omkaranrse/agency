'use client';

import * as React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { waveformBarVariants } from '@/lib/motion';

export interface AudioWaveformProps {
  state?: 'idle' | 'listening' | 'speaking';
  isActive?: boolean;
  isSpeaking?: boolean;
  barCount?: number;
  className?: string;
  barClassName?: string;
}

export function AudioWaveform({
  state: stateProp,
  isActive: isActiveProp = false,
  isSpeaking: isSpeakingProp = false,
  barCount = 12,
  className,
  barClassName,
}: AudioWaveformProps) {
  const isSpeaking = stateProp ? stateProp === 'speaking' : isSpeakingProp;
  const isActive = stateProp ? stateProp === 'listening' : isActiveProp;
  const bars = Array.from({ length: barCount }, (_, i) => i);

  return (
    <div
      className={cn('inline-flex items-center gap-1 h-6 px-2 py-1', className)}
      aria-label={
        isSpeaking
          ? 'AI Manager Speaking'
          : isActive
          ? 'Microphone Listening'
          : 'Microphone Standby'
      }
    >
      {bars.map((index) => {
        const variants = waveformBarVariants(index);
        const animState = isActive || isSpeaking ? 'active' : 'idle';

        return (
          <motion.div
            key={index}
            variants={variants}
            initial="idle"
            animate={animState}
            className={cn(
              'w-1 rounded-full origin-center transition-colors',
              isSpeaking
                ? 'bg-accent shadow-xs'
                : isActive
                ? 'bg-danger shadow-xs'
                : 'bg-muted-foreground/30',
              barClassName
            )}
            style={{
              height: '100%',
              minHeight: '4px',
            }}
          />
        );
      })}
    </div>
  );
}
