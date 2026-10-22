import { Variants, Transition } from 'framer-motion';

/**
 * Standard spring and cubic bezier easing configurations for the Command Center.
 */
export const transitions = {
  instant: { duration: 0.05, ease: 'linear' },
  micro: { duration: 0.15, ease: [0.16, 1, 0.3, 1] },
  standard: { duration: 0.25, ease: [0.16, 1, 0.3, 1] },
  smooth: { duration: 0.35, ease: [0.16, 1, 0.3, 1] },
  springQuick: { type: 'spring', stiffness: 400, damping: 28 },
  springTactile: { type: 'spring', stiffness: 350, damping: 25 },
  springGentle: { type: 'spring', stiffness: 220, damping: 22 },
  springBouncy: { type: 'spring', stiffness: 300, damping: 15 },
} as const;

/**
 * Page level entrance and exit variants.
 */
export const pageVariants: Variants = {
  hidden: {
    opacity: 0,
    y: 8,
    transition: transitions.standard,
  },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.25,
      ease: [0.16, 1, 0.3, 1],
      when: 'beforeChildren',
      staggerChildren: 0.05,
    },
  },
  exit: {
    opacity: 0,
    y: -6,
    transition: transitions.micro,
  },
};

/**
 * Staggered container variants for lists of cards or rows.
 */
export const containerStaggerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.06,
      delayChildren: 0.03,
    },
  },
};

/**
 * Item entrance within a staggered container.
 */
export const itemFadeUpVariants: Variants = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: transitions.standard,
  },
};

/**
 * Interactive card lift and hover states.
 */
export const hoverCardVariants: Variants = {
  initial: { y: 0, scale: 1 },
  hover: {
    y: -2,
    scale: 1.008,
    transition: transitions.micro,
  },
  press: {
    y: 0,
    scale: 0.99,
    transition: transitions.instant,
  },
};

/**
 * Tactile button feedback.
 */
export const tactileButtonVariants: Variants = {
  initial: { scale: 1 },
  hover: { scale: 1.02, transition: transitions.micro },
  tap: { scale: 0.97, transition: transitions.instant },
};

/**
 * Drawer / slide-over right panel.
 */
export const drawerSlideVariants: Variants = {
  hidden: { x: '100%', opacity: 0.8 },
  visible: {
    x: 0,
    opacity: 1,
    transition: transitions.springTactile,
  },
  exit: {
    x: '100%',
    opacity: 0,
    transition: { duration: 0.2, ease: [0.16, 1, 0.3, 1] },
  },
};

/**
 * Modal dialogue scale & fade.
 */
export const modalDialogVariants: Variants = {
  hidden: { opacity: 0, scale: 0.96, y: 8 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: transitions.springTactile,
  },
  exit: {
    opacity: 0,
    scale: 0.96,
    y: 4,
    transition: transitions.micro,
  },
};

/**
 * Radar / heartbeat node pulse animation.
 */
export const pulseRadarVariants: Variants = {
  initial: { scale: 0.95, opacity: 0.6 },
  animate: {
    scale: [0.95, 1.25, 0.95],
    opacity: [0.6, 0.15, 0.6],
    transition: {
      duration: 2.2,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
};

/**
 * Audio waveform frequency bars animation for voice streaming.
 */
export const waveformBarVariants = (index: number): Variants => ({
  idle: {
    scaleY: 0.25,
    opacity: 0.4,
    transition: transitions.micro,
  },
  active: {
    scaleY: [0.25, 1.0, 0.3, 0.8, 0.25],
    opacity: 1,
    transition: {
      duration: 0.8 + (index % 4) * 0.15,
      repeat: Infinity,
      repeatType: 'reverse',
      ease: 'easeInOut',
    },
  },
});
