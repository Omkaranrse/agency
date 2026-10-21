'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Layers,
  Building2,
  PlusCircle,
  Settings,
  Palette,
  X,
  Workflow,
  ChevronLeft,
  ChevronRight,
  Bot,
  Activity,
  Cpu,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { transitions } from '@/lib/motion';
import { AIManagerAvatar } from '@/components/manager/ai-manager-avatar';

export interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

export const NAV_ITEMS: NavItem[] = [
  { label: 'Runs', href: '/runs', icon: Layers },
  { label: 'Virtual office', href: '/office', icon: Building2 },
  { label: 'AI manager', href: '/manager', icon: Bot, badge: 'VOICE' },
  { label: 'New run', href: '/new-run', icon: PlusCircle },
  { label: 'Design system', href: '/design', icon: Palette },
  { label: 'Settings', href: '/settings', icon: Settings },
];

export interface AppSidebarProps {
  isMobileOpen?: boolean;
  onMobileClose?: () => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function AppSidebar({
  isMobileOpen = false,
  onMobileClose,
  isCollapsed: controlledCollapsed,
  onToggleCollapse,
}: AppSidebarProps) {
  const pathname = usePathname();
  const [internalCollapsed, setInternalCollapsed] = React.useState(false);

  // Sync collapsed state
  const isCollapsed = controlledCollapsed !== undefined ? controlledCollapsed : internalCollapsed;
  const toggleCollapse = onToggleCollapse || (() => setInternalCollapsed((prev) => !prev));

  const sidebarContent = (
    <div className="flex h-full flex-col bg-sidebar border-r border-border text-foreground select-none">
      {/* Brand / Wordmark */}
      <div className="flex h-14 items-center justify-between px-3.5 border-b border-border bg-sidebar">
        <Link
          href="/runs"
          className="flex items-center gap-2.5 font-semibold text-sm tracking-tight text-foreground hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded px-1 py-0.5 overflow-hidden"
          onClick={onMobileClose}
        >
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-accent text-accent-foreground font-mono text-xs shadow-xs font-bold">
            <Workflow className="h-4 w-4" aria-hidden="true" />
          </div>
          {!isCollapsed && (
            <motion.div
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -6 }}
              className="flex items-center gap-2"
            >
              <span className="font-semibold tracking-wider text-xs uppercase font-mono text-foreground">
                Agency
              </span>
              <span className="text-[9px] uppercase font-semibold text-accent border border-accent/30 bg-accent/10 px-1 py-0.5 rounded font-mono">
                Command
              </span>
            </motion.div>
          )}
        </Link>

        {onMobileClose && (
          <button
            type="button"
            onClick={onMobileClose}
            className="md:hidden rounded p-1 text-muted-foreground hover:text-foreground hover:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label="Close navigation menu"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Navigation List */}
      <nav aria-label="Main Navigation" className="flex-1 overflow-y-auto px-2.5 py-4 space-y-1">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive =
            pathname === item.href ||
            (item.href !== '/runs' && pathname?.startsWith(item.href)) ||
            (item.href === '/runs' && pathname === '/');

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onMobileClose}
              aria-current={isActive ? 'page' : undefined}
              title={isCollapsed ? item.label : undefined}
              className={cn(
                'group relative flex items-center gap-3 px-3 py-2 rounded-md text-xs font-medium transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring',
                isActive
                  ? 'text-accent font-semibold'
                  : 'text-muted-foreground hover:text-foreground hover:bg-surface-raised/80'
              )}
            >
              {/* Active Sliding Pill Highlight */}
              {isActive && (
                <motion.div
                  layoutId="sidebar-active-pill"
                  className="absolute inset-0 rounded-md bg-accent/10 border border-accent/25 -z-10"
                  transition={transitions.springTactile}
                />
              )}

              {item.href === '/manager' ? (
                <AIManagerAvatar size="xs" showBadge={false} className="shrink-0" />
              ) : (
                <Icon
                  className={cn(
                    'h-4 w-4 shrink-0 transition-colors',
                    isActive ? 'text-accent' : 'text-muted-foreground group-hover:text-foreground'
                  )}
                  aria-hidden="true"
                />
              )}

              {!isCollapsed && (
                <span className="truncate">{item.label}</span>
              )}

              {!isCollapsed && item.badge && (
                <span className="ml-auto text-[9px] font-mono px-1.5 py-0.2 rounded bg-surface-raised border border-border text-muted-foreground">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Desktop Collapse Toggle */}
      <div className="hidden md:flex items-center justify-between p-2.5 border-t border-border">
        {!isCollapsed && (
          <div className="flex items-center gap-2 px-1 text-[11px] text-muted-foreground">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-success" />
            </span>
            <span className="font-mono text-[10px]">Agency Online</span>
          </div>
        )}

        <button
          type="button"
          onClick={toggleCollapse}
          className={cn(
            'flex h-7 w-7 items-center justify-center rounded-md border border-border text-muted-foreground hover:text-foreground hover:bg-surface-raised transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            isCollapsed && 'mx-auto'
          )}
          aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? (
            <ChevronRight className="h-3.5 w-3.5" />
          ) : (
            <ChevronLeft className="h-3.5 w-3.5" />
          )}
        </button>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar with dynamic width */}
      <motion.aside
        animate={{ width: isCollapsed ? 68 : 240 }}
        transition={transitions.springTactile}
        className="hidden md:block shrink-0 h-screen sticky top-0 z-30"
      >
        {sidebarContent}
      </motion.aside>

      {/* Mobile Drawer */}
      {isMobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden" role="dialog" aria-modal="true">
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
            onClick={onMobileClose}
            aria-hidden="true"
          />
          <div className="fixed inset-y-0 left-0 w-64 shadow-2xl z-10">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
}
