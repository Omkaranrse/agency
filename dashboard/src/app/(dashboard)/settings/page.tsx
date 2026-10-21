'use client';

import * as React from 'react';
import { motion } from 'framer-motion';
import { PageHeader } from '@/components/ui/page-header';
import { useTheme, type Theme } from '@/components/theme/theme-provider';
import { Select } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { GlowCard } from '@/components/framer/glow-card';
import { ShimmerButton } from '@/components/framer/shimmer-button';
import { SlidingTabs } from '@/components/framer/sliding-tabs';
import { Sun, Moon, Monitor, Laptop, ShieldCheck, Cpu, HardDrive, Wifi } from 'lucide-react';

export default function SettingsPage() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [density, setDensity] = React.useState('comfortable');
  const [refreshInterval, setRefreshInterval] = React.useState('10');
  const [saveStatus, setSaveStatus] = React.useState<string | null>(null);

  React.useEffect(() => {
    try {
      const savedDensity = localStorage.getItem('agency-density');
      if (savedDensity) setDensity(savedDensity);
      const savedInterval = localStorage.getItem('agency-refresh-interval');
      if (savedInterval) setRefreshInterval(savedInterval);
    } catch {
      // localStorage may fail in restricted sandboxes
    }
  }, []);

  const handleDensityChange = (val: string) => {
    setDensity(val);
    try {
      localStorage.setItem('agency-density', val);
      setSaveStatus('Display density preferences updated');
      setTimeout(() => setSaveStatus(null), 3000);
    } catch {
      // ignore
    }
  };

  const handleIntervalChange = (val: string) => {
    setRefreshInterval(val);
    try {
      localStorage.setItem('agency-refresh-interval', val);
      setSaveStatus('Stream refresh rate updated');
      setTimeout(() => setSaveStatus(null), 3000);
    } catch {
      // ignore
    }
  };

  const themeTabs = [
    { id: 'dark', label: 'Dark Command', icon: Moon },
    { id: 'light', label: 'Light Studio', icon: Sun },
    { id: 'system', label: 'System Mode', icon: Monitor },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="space-y-6 max-w-4xl pb-12"
    >
      <PageHeader
        title="Command Center Preferences"
        description="Configure operator interface styling, streaming refresh rates, and environment parameters."
      />

      {saveStatus && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-lg border border-brand-teal/40 bg-brand-teal/10 px-3.5 py-2 text-xs text-brand-teal font-mono flex items-center justify-between"
        >
          <span>✓ {saveStatus}</span>
        </motion.div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Visual Appearance Card */}
        <GlowCard glowColor="rgba(84, 225, 193, 0.12)" className="p-5 space-y-4">
          <div>
            <h2 className="text-xs font-semibold text-foreground uppercase tracking-widest font-mono mb-1">
              Visual Atmosphere
            </h2>
            <p className="text-xs text-muted-foreground">
              Select the active theme for the command center interface.
            </p>
          </div>

          <div className="pt-1">
            <SlidingTabs
              tabs={themeTabs}
              activeTab={theme}
              onChange={(newTheme) => setTheme(newTheme as Theme)}
              className="w-full"
            />
          </div>

          <div className="pt-2 text-[11px] text-muted-foreground font-mono flex items-center justify-between border-t border-border/60">
            <span>Active Canvas Render:</span>
            <span className="text-accent uppercase font-semibold">{resolvedTheme}</span>
          </div>
        </GlowCard>

        {/* Telemetry & Performance Card */}
        <GlowCard glowColor="rgba(139, 139, 255, 0.12)" className="p-5 space-y-4">
          <div>
            <h2 className="text-xs font-semibold text-foreground uppercase tracking-widest font-mono mb-1">
              Telemetry & Sync
            </h2>
            <p className="text-xs text-muted-foreground">
              Configure background status checks and fallback poll frequencies.
            </p>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="refresh-select" className="text-xs font-medium text-foreground block">
              Fallback Polling Interval
            </label>
            <Select
              id="refresh-select"
              value={refreshInterval}
              onChange={(e) => handleIntervalChange(e.target.value)}
              className="bg-background/80 font-mono text-xs"
            >
              <option value="5">Every 5 seconds (high frequency)</option>
              <option value="10">Every 10 seconds (optimal)</option>
              <option value="30">Every 30 seconds (low bandwidth)</option>
              <option value="manual">Manual refresh only</option>
            </Select>
          </div>

          <div className="space-y-1.5 pt-1">
            <label htmlFor="density-select" className="text-xs font-medium text-foreground block">
              Information Density
            </label>
            <Select
              id="density-select"
              value={density}
              onChange={(e) => handleDensityChange(e.target.value)}
              className="bg-background/80 font-mono text-xs"
            >
              <option value="comfortable">Comfortable (default)</option>
              <option value="compact">Compact (dense telemetry view)</option>
            </Select>
          </div>
        </GlowCard>

        {/* System & Architecture Specifications */}
        <GlowCard glowColor="rgba(84, 225, 193, 0.08)" className="p-5 space-y-4 md:col-span-2">
          <div className="flex items-center justify-between border-b border-border/80 pb-3">
            <div>
              <h2 className="text-xs font-semibold text-foreground uppercase tracking-widest font-mono">
                System Infrastructure & Environment
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Deterministic execution adapters and hardware isolation parameters.
              </p>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono text-success bg-success/10 border border-success/30 flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" />
              OPERATIONAL
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 font-mono text-[11px]">
            <div className="rounded-lg border border-border/80 bg-background/50 p-3 space-y-1">
              <span className="text-[10px] text-muted-foreground uppercase block">Client Core</span>
              <span className="text-foreground font-semibold block">Next.js 14 App Router</span>
              <span className="text-accent text-[10px] block">TypeScript Strict</span>
            </div>

            <div className="rounded-lg border border-border/80 bg-background/50 p-3 space-y-1">
              <span className="text-[10px] text-muted-foreground uppercase block">Backend Service</span>
              <span className="text-foreground font-semibold block">FastAPI + LangGraph</span>
              <span className="text-accent-secondary text-[10px] block">Python 3.12 Port</span>
            </div>

            <div className="rounded-lg border border-border/80 bg-background/50 p-3 space-y-1">
              <span className="text-[10px] text-muted-foreground uppercase block">Execution Sandbox</span>
              <span className="text-foreground font-semibold block">Docker Container</span>
              <span className="text-success text-[10px] block">Network Isolated</span>
            </div>

            <div className="rounded-lg border border-border/80 bg-background/50 p-3 space-y-1">
              <span className="text-[10px] text-muted-foreground uppercase block">Motion System</span>
              <span className="text-foreground font-semibold block">Framer Motion</span>
              <span className="text-accent text-[10px] block">Hardware Accelerated</span>
            </div>
          </div>
        </GlowCard>
      </div>
    </motion.div>
  );
}
