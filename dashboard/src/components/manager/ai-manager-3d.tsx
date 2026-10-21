'use client';

import * as React from 'react';
import dynamic from 'next/dynamic';
import { useReducedMotion } from 'framer-motion';
import {
  RotateCcw,
  Sparkles,
  Mic,
  Volume2,
  AlertTriangle,
  CheckCircle2,
  Box,
  Eye,
  Info,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AIManagerAvatar, type AvatarState } from './ai-manager-avatar';
import { cn } from '@/lib/utils';

// Dynamic import with SSR disabled to prevent Three.js server hydration issues
const DynamicThreeCanvas = dynamic(
  () => import('./ai-manager-3d-canvas'),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full min-h-[340px] flex flex-col items-center justify-center gap-3 bg-surface/40 backdrop-blur-sm rounded-2xl border border-border">
        <div className="h-12 w-12 rounded-2xl bg-surface-raised border border-border flex items-center justify-center text-accent animate-pulse shadow-glow-sm">
          <Box className="h-6 w-6" />
        </div>
        <div className="text-center">
          <p className="text-xs font-semibold text-foreground">Loading 3D Cat Mascot...</p>
          <p className="text-[11px] font-mono text-muted-foreground">Rigged GLB Geometry & Motion</p>
        </div>
      </div>
    ),
  }
);

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

class Three3DErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('3D Cat Manager Canvas Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

export interface AIManager3DProps {
  state?: AvatarState;
  className?: string;
  height?: string | number;
  showControls?: boolean;
  onStateChange?: (state: AvatarState) => void;
  title?: string;
  subtitle?: string;
}

export function AIManager3D({
  state = 'idle',
  className,
  height = '380px',
  showControls = true,
  onStateChange,
  title = 'Alex Morgan',
  subtitle = 'Official 3D AI Agency Director',
}: AIManager3DProps) {
  const shouldReduceMotion = useReducedMotion();
  const [webglSupported, setWebglSupported] = React.useState<boolean | null>(null);
  const orbitRef = React.useRef<any>(null);

  // Check WebGL context support on mount
  React.useEffect(() => {
    try {
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
      setWebglSupported(Boolean(gl));
    } catch {
      setWebglSupported(false);
    }
  }, []);

  const handleResetCamera = () => {
    if (orbitRef.current) {
      orbitRef.current.reset();
    }
  };

  // State badge styling and icon
  const stateBadge = React.useMemo(() => {
    switch (state) {
      case 'speaking':
        return {
          label: 'Speaking',
          icon: <Volume2 className="h-3 w-3 text-accent animate-pulse" />,
          color: 'text-accent border-accent/40 bg-accent/10',
        };
      case 'listening':
        return {
          label: 'Listening',
          icon: <Mic className="h-3 w-3 text-accent-secondary animate-pulse" />,
          color: 'text-accent-secondary border-accent-secondary/40 bg-accent-secondary/10',
        };
      case 'thinking':
        return {
          label: 'Analyzing',
          icon: <Sparkles className="h-3 w-3 text-accent animate-spin" />,
          color: 'text-accent border-accent/40 bg-accent/10',
        };
      case 'warning':
        return {
          label: 'Needs Review',
          icon: <AlertTriangle className="h-3 w-3 text-warning" />,
          color: 'text-warning border-warning/40 bg-warning/10',
        };
      case 'error':
        return {
          label: 'Pipeline Error',
          icon: <AlertTriangle className="h-3 w-3 text-destructive" />,
          color: 'text-destructive border-destructive/40 bg-destructive/10',
        };
      case 'success':
        return {
          label: 'Milestone Green',
          icon: <CheckCircle2 className="h-3 w-3 text-success" />,
          color: 'text-success border-success/40 bg-success/10',
        };
      default:
        return {
          label: 'Executive Idle',
          icon: <span className="h-1.5 w-1.5 rounded-full bg-accent animate-ping" />,
          color: 'text-muted-foreground border-border bg-surface-raised/80',
        };
    }
  }, [state]);

  // Fallback for WebGL unsupported environments
  if (webglSupported === false) {
    return (
      <div
        className={cn(
          'relative rounded-2xl border border-border bg-surface p-6 flex flex-col items-center justify-center text-center overflow-hidden',
          className
        )}
        style={{ minHeight: height }}
      >
        <AIManagerAvatar size="hero" state={state} showBadge={false} />
        <div className="mt-4">
          <h4 className="text-sm font-semibold text-foreground">{title}</h4>
          <p className="text-xs text-muted-foreground">{subtitle} (2D Fallback)</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'relative rounded-2xl border border-border bg-surface overflow-hidden flex flex-col',
        'group transition-all duration-300 hover:border-border-hover',
        className
      )}
      style={{ minHeight: height }}
    >
      {/* Top Header Overlay */}
      <div className="absolute top-3 left-3 right-3 z-10 flex items-center justify-between pointer-events-none">
        <div className="flex items-center gap-2 pointer-events-auto">
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-surface-raised/85 backdrop-blur-md border border-border text-xs shadow-sm">
            <span className="h-2 w-2 rounded-full bg-success" />
            <span className="font-semibold text-foreground text-[11px]">{title}</span>
            <span className="text-[10px] text-muted-foreground hidden sm:inline">•</span>
            <span className="text-[10px] text-muted-foreground hidden sm:inline">3D GLB</span>
          </div>

          <div
            className={cn(
              'flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border text-[11px] font-mono backdrop-blur-md transition-all',
              stateBadge.color
            )}
          >
            {stateBadge.icon}
            <span>{stateBadge.label}</span>
          </div>
        </div>

        {/* Camera Reset & Controls */}
        {showControls && (
          <div className="flex items-center gap-1.5 pointer-events-auto">
            <Button
              variant="outline"
              size="icon"
              className="h-7 w-7 rounded-lg bg-surface-raised/80 backdrop-blur-md border-border hover:bg-surface text-muted-foreground hover:text-foreground text-xs"
              onClick={handleResetCamera}
              title="Reset 3D Camera View"
            >
              <RotateCcw className="h-3 w-3" />
            </Button>
          </div>
        )}
      </div>

      {/* 3D Canvas Viewport */}
      <div className="relative flex-1 w-full h-full min-h-[300px]">
        <Three3DErrorBoundary
          fallback={
            <div className="w-full h-full flex flex-col items-center justify-center p-6 text-center">
              <AIManagerAvatar size="hero" state={state} />
              <p className="text-xs text-muted-foreground mt-2">
                Fallback: 2D Confident Business Cat Mascot active.
              </p>
            </div>
          }
        >
          <DynamicThreeCanvas
            state={state}
            reducedMotion={Boolean(shouldReduceMotion)}
            orbitControlsRef={orbitRef}
          />
        </Three3DErrorBoundary>
      </div>

      {/* Bottom Hint Bar */}
      <div className="absolute bottom-2.5 left-3 right-3 z-10 flex items-center justify-between pointer-events-none text-[10px] text-muted-foreground font-mono">
        <span className="px-2 py-0.5 rounded-md bg-surface-raised/80 backdrop-blur-sm border border-border/60">
          Drag to orbit • Scroll to zoom
        </span>
        <span className="px-2 py-0.5 rounded-md bg-surface-raised/80 backdrop-blur-sm border border-border/60 hidden sm:inline">
          Official Mascot Model • 6 Rigged Clips
        </span>
      </div>
    </div>
  );
}

export default AIManager3D;
