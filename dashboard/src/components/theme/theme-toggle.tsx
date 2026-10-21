'use client';

import React from 'react';
import { Sun, Moon, Monitor } from 'lucide-react';
import { useTheme, type Theme } from './theme-provider';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';

export function ThemeToggle() {
  const { theme, resolvedTheme, setTheme } = useTheme();

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button
          type="button"
          aria-label={`Current theme: ${theme}. Click to change theme.`}
          className="relative inline-flex items-center justify-center h-8 w-8 rounded text-muted-foreground hover:text-foreground hover:bg-surface-raised border border-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-colors"
        >
          {resolvedTheme === 'dark' ? (
            <Moon className="h-4 w-4" aria-hidden="true" />
          ) : (
            <Sun className="h-4 w-4" aria-hidden="true" />
          )}
          <span className="sr-only">Toggle theme</span>
        </button>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={6}
          className="z-50 min-w-[130px] rounded border border-border bg-surface p-1 shadow-md text-foreground text-xs focus:outline-none"
        >
          <DropdownMenu.Item
            onClick={() => setTheme('light')}
            className={`flex items-center gap-2 px-2.5 py-1.5 rounded cursor-pointer select-none outline-none hover:bg-surface-raised focus:bg-surface-raised ${
              theme === 'light' ? 'font-medium text-accent' : 'text-foreground'
            }`}
          >
            <Sun className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Light</span>
            {theme === 'light' && <span className="ml-auto text-[10px]">✓</span>}
          </DropdownMenu.Item>
          <DropdownMenu.Item
            onClick={() => setTheme('dark')}
            className={`flex items-center gap-2 px-2.5 py-1.5 rounded cursor-pointer select-none outline-none hover:bg-surface-raised focus:bg-surface-raised ${
              theme === 'dark' ? 'font-medium text-accent' : 'text-foreground'
            }`}
          >
            <Moon className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Dark</span>
            {theme === 'dark' && <span className="ml-auto text-[10px]">✓</span>}
          </DropdownMenu.Item>
          <DropdownMenu.Item
            onClick={() => setTheme('system')}
            className={`flex items-center gap-2 px-2.5 py-1.5 rounded cursor-pointer select-none outline-none hover:bg-surface-raised focus:bg-surface-raised ${
              theme === 'system' ? 'font-medium text-accent' : 'text-foreground'
            }`}
          >
            <Monitor className="h-3.5 w-3.5" aria-hidden="true" />
            <span>System</span>
            {theme === 'system' && <span className="ml-auto text-[10px]">✓</span>}
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
