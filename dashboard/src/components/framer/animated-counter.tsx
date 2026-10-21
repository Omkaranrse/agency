'use client';

import * as React from 'react';
import { motion, useSpring, useTransform } from 'framer-motion';

export interface AnimatedCounterProps {
  value: number;
  className?: string;
  prefix?: string;
  suffix?: string;
}

export function AnimatedCounter({
  value,
  className,
  prefix = '',
  suffix = '',
}: AnimatedCounterProps) {
  const spring = useSpring(value, {
    mass: 0.8,
    stiffness: 140,
    damping: 18,
  });

  const display = useTransform(spring, (current) => Math.round(current).toLocaleString());

  React.useEffect(() => {
    spring.set(value);
  }, [spring, value]);

  return (
    <span className={className}>
      {prefix}
      <motion.span>{display}</motion.span>
      {suffix}
    </span>
  );
}
