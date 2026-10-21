'use client';

import * as React from 'react';
import { AppSidebar } from './app-sidebar';
import { AppHeader } from './app-header';

export interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [isCollapsed, setIsCollapsed] = React.useState(false);

  return (
    <div className="relative flex min-h-screen bg-background text-foreground antialiased selection:bg-accent/20 selection:text-accent">
      {/* Subtle Background Matrix Grid Overlay */}
      <div className="pointer-events-none fixed inset-0 bg-command-grid opacity-60 dark:opacity-40 -z-0" />

      {/* Sidebar */}
      <AppSidebar
        isMobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
        isCollapsed={isCollapsed}
        onToggleCollapse={() => setIsCollapsed((prev) => !prev)}
      />

      {/* Main column */}
      <div className="relative z-10 flex flex-1 flex-col min-w-0">
        <AppHeader onMobileMenuToggle={() => setMobileOpen(true)} />
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}

export default AppShell;
