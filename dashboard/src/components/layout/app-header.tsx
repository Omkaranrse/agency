'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Menu, Plus, Activity, ShieldCheck, Terminal, Bot } from 'lucide-react';
import { ThemeToggle } from '@/components/theme/theme-toggle';
import { Breadcrumbs, type BreadcrumbItem } from './breadcrumbs';
import { Button } from '@/components/ui/button';
import { AIManagerAvatar } from '@/components/manager/ai-manager-avatar';

export interface AppHeaderProps {
  onMobileMenuToggle: () => void;
}

function getBreadcrumbsForPath(pathname: string): BreadcrumbItem[] {
  if (!pathname || pathname === '/' || pathname === '/runs') {
    return [{ label: 'Runs' }];
  }
  if (pathname.startsWith('/office')) {
    return [
      { label: 'Runs', href: '/runs' },
      { label: 'Virtual office' },
    ];
  }
  if (pathname.startsWith('/manager')) {
    return [
      { label: 'Runs', href: '/runs' },
      { label: 'AI Manager' },
    ];
  }
  if (pathname.startsWith('/new-run')) {
    return [
      { label: 'Runs', href: '/runs' },
      { label: 'New run' },
    ];
  }
  if (pathname.startsWith('/settings')) {
    return [{ label: 'Settings' }];
  }
  if (pathname.startsWith('/design')) {
    return [{ label: 'Design system' }];
  }
  if (pathname.startsWith('/runs/')) {
    const runId = pathname.split('/runs/')[1];
    return [
      { label: 'Runs', href: '/runs' },
      { label: `Run: ${runId ? runId.slice(0, 8) : 'Detail'}` },
    ];
  }
  return [{ label: pathname.replace('/', '') }];
}

export function AppHeader({ onMobileMenuToggle }: AppHeaderProps) {
  const pathname = usePathname();
  const breadcrumbs = getBreadcrumbsForPath(pathname || '');

  return (
    <header className="sticky top-0 z-20 flex h-14 w-full items-center justify-between border-b border-border bg-surface/85 backdrop-blur-md px-4 sm:px-6 transition-colors">
      <div className="flex items-center gap-3">
        {/* Mobile menu button */}
        <button
          type="button"
          onClick={onMobileMenuToggle}
          className="md:hidden inline-flex items-center justify-center h-8 w-8 rounded text-muted-foreground hover:text-foreground hover:bg-surface-raised border border-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-label="Open navigation menu"
        >
          <Menu className="h-4 w-4" />
        </button>

        {/* Breadcrumbs */}
        <Breadcrumbs items={breadcrumbs} />
      </div>

      {/* Right controls: Status indicator + Theme toggle + Operator */}
      <div className="flex items-center gap-2.5">
        {/* Live System Status Indicator */}
        <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-border bg-surface-raised/60 text-[10px] font-mono text-muted-foreground">
          <span className="relative flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-success" />
          </span>
          <span>Pipeline Online</span>
        </div>

        {/* Quick New Run Button */}
        {!pathname?.startsWith('/new-run') && (
          <Link href="/new-run" className="hidden sm:inline-block">
            <Button size="sm" className="h-8 text-xs px-3 gap-1.5 shadow-xs font-medium">
              <Plus className="h-3.5 w-3.5" />
              <span>New Run</span>
            </Button>
          </Link>
        )}

        {/* AI Manager Quick Launch */}
        <Link href="/manager">
          <Button
            variant="outline"
            size="sm"
            className="h-8 text-xs px-2 gap-1.5 border-accent/30 text-foreground hover:bg-accent/10 shadow-xs"
            title="Open AI Manager Console"
          >
            <AIManagerAvatar size="xs" showBadge={false} />
            <span className="hidden md:inline font-mono text-[11px] text-accent">AI Manager</span>
          </Button>
        </Link>

        <ThemeToggle />

        {/* Operator Profile Badge */}
        <div className="flex items-center gap-2 pl-2 border-l border-border text-xs">
          <div
            className="flex h-7 w-7 items-center justify-center rounded-md bg-surface-raised border border-border text-[11px] font-semibold text-foreground select-none"
            title="Local Operator: operator@agency.run"
          >
            OP
          </div>
          <div className="hidden sm:flex flex-col text-left">
            <span className="text-[11px] font-medium text-foreground leading-tight">Operator</span>
            <span className="text-[9px] font-mono text-muted-foreground leading-tight">admin</span>
          </div>
        </div>
      </div>
    </header>
  );
}
