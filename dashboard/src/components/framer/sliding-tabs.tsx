'use client';

import * as React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

export interface TabItem<T extends string = string> {
  id: T;
  label: string;
  icon?: React.ComponentType<{ className?: string }>;
  badge?: string | number;
}

export interface SlidingTabsProps<T extends string = string> {
  tabs: TabItem<T>[];
  activeTab: T;
  onChange: (id: T) => void;
  className?: string;
  tabClassName?: string;
  layoutId?: string;
}

export function SlidingTabs<T extends string = string>({
  tabs,
  activeTab,
  onChange,
  className,
  tabClassName,
  layoutId = 'sliding-pill',
}: SlidingTabsProps<T>) {
  return (
    <div
      role="tablist"
      className={cn(
        'inline-flex items-center rounded-lg border border-border bg-surface p-1 text-xs select-none shadow-xs',
        className
      )}
    >
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        const Icon = tab.icon;

        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={cn(
              'relative flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring z-10',
              isActive
                ? 'text-foreground font-semibold'
                : 'text-muted-foreground hover:text-foreground',
              tabClassName
            )}
          >
            {isActive && (
              <motion.div
                layoutId={layoutId}
                className="absolute inset-0 rounded-md bg-surface-raised border border-border/80 shadow-xs -z-10"
                transition={{
                  type: 'spring',
                  stiffness: 450,
                  damping: 32,
                }}
              />
            )}
            {Icon && <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />}
            <span>{tab.label}</span>
            {tab.badge !== undefined && (
              <span
                className={cn(
                  'text-[10px] font-mono px-1.5 py-0.2 rounded-full border',
                  isActive
                    ? 'bg-accent/15 border-accent/30 text-accent font-semibold'
                    : 'bg-muted/30 border-border text-muted-foreground'
                )}
              >
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
