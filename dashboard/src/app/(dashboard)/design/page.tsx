'use client';

import * as React from 'react';
import { PageHeader } from '@/components/ui/page-header';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select } from '@/components/ui/select';
import { StatusBadge } from '@/components/ui/status-badge';
import { DataTable, type ColumnDef } from '@/components/ui/data-table';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { ErrorState } from '@/components/ui/error-state';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';
import { SimpleTooltip } from '@/components/ui/tooltip';
import { Separator } from '@/components/ui/separator';
import { DESIGN_TOKENS, type RunStatus } from '@/lib/design-tokens';
import {
  Layers,
  Info,
  Check,
  Trash2,
  ExternalLink,
  RefreshCw,
  Search,
  Sparkles,
  Volume2,
  Mic,
  Activity,
  Plus,
  Minus,
} from 'lucide-react';
import {
  GlowCard,
  ShimmerButton,
  SlidingTabs,
  TextScramble,
  AnimatedCounter,
  AudioWaveform,
} from '@/components/framer';

// Clearly labeled local demonstration data
interface DemoRun {
  id: string;
  client: string;
  archetype: string;
  status: RunStatus;
  pages: number;
  updatedAt: string;
}

const DEMO_RUNS: DemoRun[] = [
  {
    id: 'run-0192a',
    client: 'Nordic Craft Furniture',
    archetype: 'E-Commerce / Showcase',
    status: 'completed',
    pages: 5,
    updatedAt: '12m ago',
  },
  {
    id: 'run-0192b',
    client: 'Apex Capital Partners',
    archetype: 'Financial Advisory',
    status: 'awaiting_approval',
    pages: 4,
    updatedAt: '24m ago',
  },
  {
    id: 'run-0192c',
    client: 'Verdant Botanical Labs',
    archetype: 'SaaS Product',
    status: 'building',
    pages: 6,
    updatedAt: '1h ago',
  },
  {
    id: 'run-0192d',
    client: 'Studio Kura Architecture',
    archetype: 'Portfolio',
    status: 'testing',
    pages: 3,
    updatedAt: '2h ago',
  },
  {
    id: 'run-0192e',
    client: 'Meridian Logistics Group',
    archetype: 'Enterprise Portal',
    status: 'planning',
    pages: 8,
    updatedAt: '3h ago',
  },
  {
    id: 'run-0192f',
    client: 'Legacy Retailers Group',
    archetype: 'Commerce',
    status: 'failed',
    pages: 2,
    updatedAt: '5h ago',
  },
  {
    id: 'run-0192g',
    client: 'Orion Data Systems',
    archetype: 'Developer Documentation',
    status: 'cancelled',
    pages: 4,
    updatedAt: '1d ago',
  },
];

const ALL_RUN_STATUSES: RunStatus[] = [
  'created',
  'planning',
  'awaiting_approval',
  'building',
  'testing',
  'deploying',
  'completed',
  'failed',
  'cancelled',
];

export default function DesignShowcasePage() {
  const [tableState, setTableState] = React.useState<'data' | 'loading' | 'empty' | 'error'>('data');
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [dialogDestructive, setDialogDestructive] = React.useState(false);
  const [dialogLoading, setDialogLoading] = React.useState(false);
  const [actionMessage, setActionMessage] = React.useState<string | null>(null);

  // Framer Marketplace Component Showcase State
  const [demoCounter, setDemoCounter] = React.useState(1284);
  const [scrambleKey, setScrambleKey] = React.useState(0);
  const [waveformState, setWaveformState] = React.useState<'idle' | 'listening' | 'speaking'>('speaking');
  const [demoTab, setDemoTab] = React.useState('telemetry');

  const handleConfirmAction = async () => {
    setDialogLoading(true);
    await new Promise((resolve) => setTimeout(resolve, 800));
    setDialogLoading(false);
    setDialogOpen(false);
    setActionMessage(
      dialogDestructive
        ? 'Confirmed destructive action: Demonstration run cancelled.'
        : 'Confirmed standard action: Prototype approved.'
    );
    setTimeout(() => setActionMessage(null), 4000);
  };

  const columns: ColumnDef<DemoRun>[] = [
    {
      id: 'id',
      header: 'Run ID',
      accessorKey: 'id',
      className: 'font-mono text-[11px] text-muted-foreground',
    },
    {
      id: 'client',
      header: 'Client / Project',
      cell: (item) => (
        <div>
          <span className="font-medium text-foreground">{item.client}</span>
          <div className="text-[11px] text-muted-foreground">{item.archetype}</div>
        </div>
      ),
    },
    {
      id: 'status',
      header: 'Pipeline Status',
      cell: (item) => <StatusBadge status={item.status} />,
    },
    {
      id: 'pages',
      header: 'Pages',
      accessorKey: 'pages',
      className: 'text-right font-mono',
      headerClassName: 'text-right',
    },
    {
      id: 'updatedAt',
      header: 'Updated',
      accessorKey: 'updatedAt',
      className: 'text-muted-foreground text-[11px]',
    },
    {
      id: 'actions',
      header: 'Action',
      headerClassName: 'text-right',
      className: 'text-right',
      cell: (item) => (
        <Button
          variant="ghost"
          size="sm"
          className="h-6 px-2 text-[11px]"
          onClick={() => {
            setDialogDestructive(false);
            setDialogOpen(true);
          }}
        >
          Review
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-10 pb-12">
      <PageHeader
        title="Design System & Component Showcase"
        description="Comprehensive verification showcase for Agency design tokens, typography, form controls, badges, and layout primitives."
        actions={
          <div className="flex items-center gap-2">
            <span className="rounded border border-border bg-surface px-2 py-1 text-[11px] font-mono text-muted-foreground">
              Phase 12 Showcase
            </span>
          </div>
        }
      />

      {/* Confirmation banner */}
      {actionMessage && (
        <div
          role="status"
          className="flex items-center gap-2 rounded border border-success/30 bg-success-surface p-3 text-xs text-success"
        >
          <Check className="h-4 w-4 shrink-0" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* Section 0: Futuristic Framer Marketplace & Motion Suite */}
      <section className="space-y-4" aria-labelledby="framer-heading">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-brand-teal" />
            <h2 id="framer-heading" className="text-sm font-semibold tracking-wide uppercase text-foreground">
              0. Framer Marketplace & Motion Interaction Suite
            </h2>
          </div>
          <span className="text-[11px] font-mono text-brand-teal px-2 py-0.5 rounded bg-brand-teal/10 border border-brand-teal/30">
            Hardware Accelerated
          </span>
        </div>
        <p className="text-xs text-muted-foreground">
          Recreated and adapted from top free Framer Marketplace interaction patterns documented in <code className="rounded bg-surface-raised px-1 py-0.5 font-mono text-[11px]">docs/framer-component-inventory.md</code>. Featuring radial spotlight tracking, metallic button shimmers, rolling ticker counters, voice waveforms, and cryptographic text reveals.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* 1. Glow Card with Cursor Spotlight */}
          <GlowCard glowColor="rgba(84, 225, 193, 0.15)" className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-brand-teal uppercase tracking-wider">
                Pattern: Spotlight Card
              </span>
              <span className="h-1.5 w-1.5 rounded-full bg-brand-teal animate-pulse" />
            </div>
            <h3 className="text-xs font-semibold text-foreground">Interactive Radial Glow</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Move your cursor over this card. A smooth radial gradient spotlight follows pointer coordinates with dynamic depth.
            </p>
            <div className="pt-2 flex items-center justify-between border-t border-border/60 text-[10px] font-mono text-muted-foreground">
              <span>FPS: 60 (CSS Variables)</span>
              <span className="text-brand-teal">Zero Layout Shift</span>
            </div>
          </GlowCard>

          {/* 2. Shimmer Button & Tactile Springs */}
          <GlowCard glowColor="rgba(131, 169, 255, 0.15)" className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-brand-blue uppercase tracking-wider">
                Pattern: Shimmer Button
              </span>
            </div>
            <h3 className="text-xs font-semibold text-foreground">Tactile Micro-Springs</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Hover to trigger the continuous metallic edge sweep. Tap to experience damped spring compression.
            </p>
            <div className="pt-1 flex flex-wrap gap-2">
              <ShimmerButton size="sm">Primary Shimmer</ShimmerButton>
              <ShimmerButton size="sm" variant="outline">Outline</ShimmerButton>
            </div>
          </GlowCard>

          {/* 3. Text Scramble Cryptographic Reveal */}
          <GlowCard glowColor="rgba(84, 225, 193, 0.15)" className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-brand-teal uppercase tracking-wider">
                Pattern: Terminal Decrypt
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="h-5 px-1.5 text-[10px] font-mono text-brand-teal"
                onClick={() => setScrambleKey((k) => k + 1)}
              >
                RE-SCRAMBLE
              </Button>
            </div>
            <h3 className="text-xs font-semibold text-foreground">Cryptographic Text Reveal</h3>
            <div className="p-2.5 rounded-lg bg-background/80 border border-border/80 font-mono text-xs text-brand-teal">
              <TextScramble
                key={scrambleKey}
                text="AUTONOMOUS AGENT ACTIVE // ORCHESTRATION OK"
              />
            </div>
            <p className="text-[11px] text-muted-foreground">
              Simulates real-time matrix decoding during agent state transitions.
            </p>
          </GlowCard>

          {/* 4. Sliding Pill Tabs */}
          <GlowCard glowColor="rgba(131, 169, 255, 0.15)" className="p-4 space-y-3 md:col-span-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-brand-blue uppercase tracking-wider">
                Pattern: Segmented Control
              </span>
              <span className="text-[10px] font-mono text-muted-foreground">Framer layoutId</span>
            </div>
            <h3 className="text-xs font-semibold text-foreground">Fluid Sliding Pill Segmented Tabs</h3>
            <SlidingTabs
              tabs={[
                { id: 'telemetry', label: 'Agent Telemetry', icon: Activity },
                { id: 'voice', label: 'Voice Visualizer', icon: Volume2 },
                { id: 'counters', label: 'Live Metrics', icon: Sparkles },
              ]}
              activeTab={demoTab}
              onChange={setDemoTab}
              className="w-full"
            />
            <div className="text-[11px] font-mono text-muted-foreground p-2 rounded bg-background/50 border border-border/60">
              Active Segment: <strong className="text-foreground capitalize">{demoTab}</strong>
            </div>
          </GlowCard>

          {/* 5. Animated Counter Ticker */}
          <GlowCard glowColor="rgba(72, 199, 142, 0.15)" className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-success uppercase tracking-wider">
                Pattern: Rolling Ticker
              </span>
            </div>
            <h3 className="text-xs font-semibold text-foreground">Animated Numeric Counter</h3>
            <div className="flex items-center justify-between p-3 rounded-lg bg-background/80 border border-border/80">
              <span className="text-2xl font-mono font-bold text-success tabular-nums">
                <AnimatedCounter value={demoCounter} />
              </span>
              <div className="flex items-center gap-1.5">
                <Button
                  variant="outline"
                  size="icon-sm"
                  onClick={() => setDemoCounter((c) => Math.max(0, c - 25))}
                  title="Decrement counter"
                >
                  <Minus className="h-3 w-3" />
                </Button>
                <Button
                  variant="outline"
                  size="icon-sm"
                  onClick={() => setDemoCounter((c) => c + 75)}
                  title="Increment counter"
                >
                  <Plus className="h-3 w-3" />
                </Button>
              </div>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Smooth spring transitions on metric changes without layout pop.
            </p>
          </GlowCard>

          {/* 6. Dynamic Voice Frequency Waveform */}
          <GlowCard glowColor="rgba(84, 225, 193, 0.15)" className="p-4 space-y-3 md:col-span-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-brand-teal uppercase tracking-wider">
                  Pattern: Audio Frequency Visualizer
                </span>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-brand-teal/10 text-brand-teal border border-brand-teal/30 capitalize">
                  {waveformState}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <Button
                  variant={waveformState === 'idle' ? 'primary' : 'outline'}
                  size="sm"
                  className="h-6 px-2 text-[10px]"
                  onClick={() => setWaveformState('idle')}
                >
                  Idle
                </Button>
                <Button
                  variant={waveformState === 'listening' ? 'primary' : 'outline'}
                  size="sm"
                  className="h-6 px-2 text-[10px]"
                  onClick={() => setWaveformState('listening')}
                >
                  Listening
                </Button>
                <Button
                  variant={waveformState === 'speaking' ? 'primary' : 'outline'}
                  size="sm"
                  className="h-6 px-2 text-[10px]"
                  onClick={() => setWaveformState('speaking')}
                >
                  Speaking
                </Button>
              </div>
            </div>
            <h3 className="text-xs font-semibold text-foreground">12-Band AI Voice Frequency Visualizer</h3>
            <div className="p-4 rounded-xl bg-background/80 border border-border/80 flex items-center justify-center">
              <AudioWaveform state={waveformState} barCount={18} className="h-12 w-full max-w-md" />
            </div>
          </GlowCard>
        </div>
      </section>

      {/* Section 1: Color Tokens */}
      <section className="space-y-4" aria-labelledby="tokens-heading">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <h2 id="tokens-heading" className="text-sm font-semibold tracking-wide uppercase text-foreground">
            1. Design Tokens & Palette
          </h2>
          <span className="text-[11px] text-muted-foreground">CSS Custom Properties</span>
        </div>
        <p className="text-xs text-muted-foreground">
          Core tokens defined in <code className="rounded bg-surface-raised px-1 py-0.5 font-mono text-[11px]">globals.css</code>. Restrained, information-dense, high-contrast palette adhering strictly to brand values without gradients or neon effects.
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
          <div className="rounded border border-border bg-surface p-3 space-y-1.5">
            <div className="h-8 w-full rounded border border-border bg-background" />
            <div className="text-xs font-medium text-foreground">Background</div>
            <div className="font-mono text-[11px] text-muted-foreground">#F7F6F3 / #16181D</div>
          </div>

          <div className="rounded border border-border bg-surface p-3 space-y-1.5">
            <div className="h-8 w-full rounded border border-border bg-surface" />
            <div className="text-xs font-medium text-foreground">Surface</div>
            <div className="font-mono text-[11px] text-muted-foreground">#FFFFFF / #1F242C</div>
          </div>

          <div className="rounded border border-border bg-surface p-3 space-y-1.5">
            <div className="h-8 w-full rounded border border-border bg-border" />
            <div className="text-xs font-medium text-foreground">Border</div>
            <div className="font-mono text-[11px] text-muted-foreground">#E4E1DA / #2E3440</div>
          </div>

          <div className="rounded border border-border bg-surface p-3 space-y-1.5">
            <div className="h-8 w-full rounded bg-foreground" />
            <div className="text-xs font-medium text-foreground">Text</div>
            <div className="font-mono text-[11px] text-muted-foreground">#1F2328 / #ECEFF4</div>
          </div>

          <div className="rounded border border-border bg-surface p-3 space-y-1.5">
            <div className="h-8 w-full rounded bg-muted-foreground" />
            <div className="text-xs font-medium text-foreground">Muted Text</div>
            <div className="font-mono text-[11px] text-muted-foreground">#6B7280 / #9CA3AF</div>
          </div>

          <div className="rounded border border-border bg-surface p-3 space-y-1.5">
            <div className="h-8 w-full rounded bg-accent" />
            <div className="text-xs font-medium text-foreground">Accent (Brand)</div>
            <div className="font-mono text-[11px] text-muted-foreground">#2C5F5A / #4C8B82</div>
          </div>

          <div className="rounded border border-border bg-surface p-3 space-y-1.5">
            <div className="h-8 w-full rounded bg-success" />
            <div className="text-xs font-medium text-foreground">Success</div>
            <div className="font-mono text-[11px] text-muted-foreground">#3D7A4F / #4E9A66</div>
          </div>

          <div className="rounded border border-border bg-surface p-3 space-y-1.5">
            <div className="h-8 w-full rounded bg-warning" />
            <div className="text-xs font-medium text-foreground">Warning</div>
            <div className="font-mono text-[11px] text-muted-foreground">#B7791F / #D08770</div>
          </div>

          <div className="rounded border border-border bg-surface p-3 space-y-1.5">
            <div className="h-8 w-full rounded bg-danger" />
            <div className="text-xs font-medium text-foreground">Danger</div>
            <div className="font-mono text-[11px] text-muted-foreground">#B4443C / #BF616A</div>
          </div>

          <div className="rounded border border-border bg-surface p-3 space-y-1.5">
            <div className="h-8 w-full rounded bg-surface-raised border border-border" />
            <div className="text-xs font-medium text-foreground">Surface Raised</div>
            <div className="font-mono text-[11px] text-muted-foreground">#F0EFEA / #282E38</div>
          </div>
        </div>
      </section>

      {/* Section 2: Typography Hierarchy */}
      <section className="space-y-4" aria-labelledby="typography-heading">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <h2 id="typography-heading" className="text-sm font-semibold tracking-wide uppercase text-foreground">
            2. Typography Hierarchy (Poppins)
          </h2>
          <span className="text-[11px] text-muted-foreground">400, 500, 600</span>
        </div>

        <div className="rounded border border-border bg-surface p-5 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 items-baseline gap-2 border-b border-border/60 pb-3">
            <span className="font-mono text-[11px] text-muted-foreground">H1 Page Title (20px / 600)</span>
            <div className="md:col-span-3 text-xl font-semibold tracking-tight text-foreground">
              Automated Website Generation Pipeline
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 items-baseline gap-2 border-b border-border/60 pb-3">
            <span className="font-mono text-[11px] text-muted-foreground">H2 Section Title (16px / 600)</span>
            <div className="md:col-span-3 text-base font-semibold text-foreground">
              Client Brief & Architectural Specification
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 items-baseline gap-2 border-b border-border/60 pb-3">
            <span className="font-mono text-[11px] text-muted-foreground">H3 Subheading (14px / 500)</span>
            <div className="md:col-span-3 text-sm font-medium text-foreground">
              QA Test Verification Matrix & Accessibility Audits
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 items-baseline gap-2 border-b border-border/60 pb-3">
            <span className="font-mono text-[11px] text-muted-foreground">Body Text (14px / 400)</span>
            <div className="md:col-span-3 text-sm text-foreground leading-relaxed">
              Agency orchestrates a multi-agent workflow consisting of Project Manager, Designer, and Builder agents to translate unstructured client briefs into production-grade websites.
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 items-baseline gap-2 border-b border-border/60 pb-3">
            <span className="font-mono text-[11px] text-muted-foreground">Muted / Caption (12px / 400)</span>
            <div className="md:col-span-3 text-xs text-muted-foreground">
              Last synchronized 2 minutes ago via Cloudflare Pages deployment adapter.
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 items-baseline gap-2">
            <span className="font-mono text-[11px] text-muted-foreground">Monospace (12px / 400)</span>
            <div className="md:col-span-3 font-mono text-xs text-foreground">
              GET /api/v1/runs/run-0192a/status -&gt; 200 OK (38ms)
            </div>
          </div>
        </div>
      </section>

      {/* Section 3: Status Badges */}
      <section className="space-y-4" aria-labelledby="status-badges-heading">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <h2 id="status-badges-heading" className="text-sm font-semibold tracking-wide uppercase text-foreground">
            3. Pipeline Status Badges
          </h2>
          <span className="text-[11px] text-muted-foreground">All 9 Domain States</span>
        </div>
        <p className="text-xs text-muted-foreground">
          Never relies on color alone; includes distinct semantic Lucide icons, readable text labels, and compliant contrast ratios.
        </p>

        <div className="rounded border border-border bg-surface p-5">
          <div className="flex flex-wrap gap-2.5 items-center">
            {ALL_RUN_STATUSES.map((status) => (
              <StatusBadge key={status} status={status} size="default" />
            ))}
          </div>

          <div className="mt-4 pt-4 border-t border-border/60 flex flex-wrap gap-2.5 items-center">
            <span className="text-[11px] text-muted-foreground mr-2 font-mono">Small variant:</span>
            {ALL_RUN_STATUSES.map((status) => (
              <StatusBadge key={`sm-${status}`} status={status} size="sm" />
            ))}
          </div>
        </div>
      </section>

      {/* Section 4: Buttons */}
      <section className="space-y-4" aria-labelledby="buttons-heading">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <h2 id="buttons-heading" className="text-sm font-semibold tracking-wide uppercase text-foreground">
            4. Button Variants & States
          </h2>
          <span className="text-[11px] text-muted-foreground">Primary, Secondary, Outline, Ghost, Destructive</span>
        </div>

        <div className="rounded border border-border bg-surface p-5 space-y-4">
          <div className="flex flex-wrap items-center gap-2.5">
            <Button variant="primary">Primary</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="outline">Outline</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="destructive">Destructive</Button>
            <Button variant="primary" isLoading loadingText="Building...">
              Loading
            </Button>
            <Button variant="outline" disabled>
              Disabled
            </Button>
            <SimpleTooltip content="Search runs">
              <Button variant="outline" size="icon" aria-label="Search runs">
                <Search className="h-3.5 w-3.5" />
              </Button>
            </SimpleTooltip>
          </div>

          <div className="pt-3 border-t border-border/60 flex flex-wrap items-center gap-2.5">
            <span className="text-[11px] text-muted-foreground mr-2 font-mono">Sizes:</span>
            <Button variant="primary" size="sm">Small (sm)</Button>
            <Button variant="primary" size="default">Default</Button>
            <Button variant="primary" size="lg">Large (lg)</Button>
          </div>
        </div>
      </section>

      {/* Section 5: Form Controls */}
      <section className="space-y-4" aria-labelledby="forms-heading">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <h2 id="forms-heading" className="text-sm font-semibold tracking-wide uppercase text-foreground">
            5. Form Controls & Validation States
          </h2>
          <span className="text-[11px] text-muted-foreground">Input, Textarea, Select</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 rounded border border-border bg-surface p-5">
          <div className="space-y-1.5">
            <label htmlFor="demo-input-normal" className="block text-xs font-medium text-foreground">
              Normal Input
            </label>
            <Input id="demo-input-normal" placeholder="Standard text input..." defaultValue="Client Website #42" />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="demo-input-error" className="block text-xs font-medium text-foreground">
              Input with Error State
            </label>
            <Input id="demo-input-error" error defaultValue="invalid-url-format" aria-describedby="demo-error-msg" />
            <p id="demo-error-msg" className="text-[11px] text-danger">
              Please enter a valid RFC-3986 URL or branch name.
            </p>
          </div>

          <div className="space-y-1.5">
            <label htmlFor="demo-input-disabled" className="block text-xs font-medium text-foreground">
              Disabled Input
            </label>
            <Input id="demo-input-disabled" disabled value="System managed identifier" />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="demo-select" className="block text-xs font-medium text-foreground">
              Styled Select Control
            </label>
            <Select id="demo-select" defaultValue="production">
              <option value="staging">Staging Environment (CF Pages)</option>
              <option value="production">Production Environment (CF Pages)</option>
              <option value="local">Local Docker Sandbox</option>
            </Select>
          </div>

          <div className="md:col-span-2 space-y-1.5">
            <label htmlFor="demo-textarea" className="block text-xs font-medium text-foreground">
              Textarea Control
            </label>
            <Textarea
              id="demo-textarea"
              rows={3}
              placeholder="Multi-line notes, design instructions, or feedback..."
              defaultValue="Prioritize mobile layout clarity on the about page."
            />
          </div>
        </div>
      </section>

      {/* Section 6: Data Table & Interactive States */}
      <section className="space-y-4" aria-labelledby="table-heading">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-border pb-2 gap-2">
          <div>
            <h2 id="table-heading" className="text-sm font-semibold tracking-wide uppercase text-foreground">
              6. Data Table & States
            </h2>
            <p className="text-xs text-muted-foreground">
              Demonstration data clearly labeled. Toggle view mode to preview all states.
            </p>
          </div>

          <div className="flex items-center gap-1.5">
            <Button
              variant={tableState === 'data' ? 'primary' : 'outline'}
              size="sm"
              onClick={() => setTableState('data')}
            >
              Data View
            </Button>
            <Button
              variant={tableState === 'loading' ? 'primary' : 'outline'}
              size="sm"
              onClick={() => setTableState('loading')}
            >
              Skeleton Loading
            </Button>
            <Button
              variant={tableState === 'empty' ? 'primary' : 'outline'}
              size="sm"
              onClick={() => setTableState('empty')}
            >
              Empty State
            </Button>
            <Button
              variant={tableState === 'error' ? 'primary' : 'outline'}
              size="sm"
              onClick={() => setTableState('error')}
            >
              Error State
            </Button>
          </div>
        </div>

        <DataTable
          columns={columns}
          data={tableState === 'data' ? DEMO_RUNS : []}
          keyExtractor={(item) => item.id}
          isLoading={tableState === 'loading'}
          loadingRowCount={5}
          caption="Demonstration website runs table"
          emptyState={
            <EmptyState
              icon={Layers}
              title="No demonstration runs found"
              description="Switch back to Data View to preview table rows."
              action={
                <Button variant="outline" size="sm" onClick={() => setTableState('data')}>
                  Reset to Data View
                </Button>
              }
            />
          }
          errorState={
            tableState === 'error' ? (
              <ErrorState
                title="Failed to fetch demonstration records"
                message="A transient network or timeout error occurred while retrieving run telemetry."
                referenceId="ERR_DEMO_TABLE_TIMEOUT_504"
                onRetry={() => setTableState('data')}
              />
            ) : undefined
          }
        />
      </section>

      {/* Section 7: Dialogs & Tooltips */}
      <section className="space-y-4" aria-labelledby="modals-heading">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <h2 id="modals-heading" className="text-sm font-semibold tracking-wide uppercase text-foreground">
            7. Dialogs, Modals & Tooltips
          </h2>
          <span className="text-[11px] text-muted-foreground">Accessible Radix Primitives</span>
        </div>

        <div className="flex flex-wrap items-center gap-3 rounded border border-border bg-surface p-5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setDialogDestructive(false);
              setDialogOpen(true);
            }}
          >
            Open Standard Confirm Dialog
          </Button>

          <Button
            variant="destructive"
            size="sm"
            onClick={() => {
              setDialogDestructive(true);
              setDialogOpen(true);
            }}
          >
            Open Destructive Confirm Dialog
          </Button>

          <SimpleTooltip content="Accessible tooltip using @radix-ui/react-tooltip">
            <span className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground cursor-help p-1 rounded border border-dashed border-border">
              <Info className="h-3.5 w-3.5" />
              <span>Hover for tooltip</span>
            </span>
          </SimpleTooltip>
        </div>

        {/* Modal instance */}
        <ConfirmDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          title={dialogDestructive ? 'Cancel Website Generation Run?' : 'Approve Prototype Design?'}
          description={
            dialogDestructive
              ? 'This will immediately abort the background Builder agent execution in the Docker sandbox and release all allocated tokens.'
              : 'Approving this prototype will advance the pipeline to the automated QA and Cloudflare Pages deployment stages.'
          }
          confirmLabel={dialogDestructive ? 'Cancel Run' : 'Approve Prototype'}
          cancelLabel="Keep Reviewing"
          isDestructive={dialogDestructive}
          isLoading={dialogLoading}
          onConfirm={handleConfirmAction}
        />
      </section>

      {/* Section 8: Skeletons & Fallbacks */}
      <section className="space-y-4" aria-labelledby="skeletons-heading">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <h2 id="skeletons-heading" className="text-sm font-semibold tracking-wide uppercase text-foreground">
            8. Loading Placeholders (Reduced-Motion Aware)
          </h2>
          <span className="text-[11px] text-muted-foreground">Accessible Skeleton Primitives</span>
        </div>

        <div className="rounded border border-border bg-surface p-5 space-y-3">
          <div className="space-y-2">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-3 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
          <div className="flex items-center gap-3 pt-2">
            <Skeleton className="h-8 w-24" />
            <Skeleton className="h-8 w-24" />
          </div>
        </div>
      </section>
    </div>
  );
}
