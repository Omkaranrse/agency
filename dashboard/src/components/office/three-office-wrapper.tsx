'use client';

import * as React from 'react';
import dynamic from 'next/dynamic';
import { Skeleton } from '@/components/ui/skeleton';
import { AlertCircle, Box, Monitor } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { AgentRole, OfficeEmployeeState, WorkstationState } from '@/features/office/types';

const DynamicThreeCanvas = dynamic(
  () => import('./three-office-canvas'),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-[520px] rounded-xl border border-border bg-surface/50 flex flex-col items-center justify-center gap-3">
        <div className="h-10 w-10 rounded-xl bg-surface-raised border border-border flex items-center justify-center text-accent animate-pulse">
          <Box className="h-5 w-5" />
        </div>
        <span className="text-xs font-mono text-muted-foreground">
          Initializing WebGL Spatial Engine...
        </span>
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

class ThreeErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Three.js Virtual Office Render Failure:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

export interface ThreeOfficeWrapperProps {
  employees: OfficeEmployeeState[];
  workstations: WorkstationState[];
  selectedRole: AgentRole | null;
  onSelectRole: (role: AgentRole) => void;
  onSwitchToTableView?: () => void;
}

export function ThreeOfficeWrapper({
  employees,
  workstations,
  selectedRole,
  onSelectRole,
  onSwitchToTableView,
}: ThreeOfficeWrapperProps) {
  const [webglSupported, setWebglSupported] = React.useState<boolean | null>(null);

  React.useEffect(() => {
    try {
      const canvas = document.createElement('canvas');
      const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
      setWebglSupported(Boolean(gl));
    } catch {
      setWebglSupported(false);
    }
  }, []);

  if (webglSupported === false) {
    return (
      <div className="w-full h-[320px] rounded-xl border border-warning/40 bg-warning/5 p-6 flex flex-col items-center justify-center text-center">
        <Monitor className="h-8 w-8 text-warning mb-2" />
        <h3 className="text-sm font-semibold text-foreground mb-1">
          WebGL Acceleration Unavailable
        </h3>
        <p className="text-xs text-muted-foreground max-w-sm mb-4">
          Your browser or device environment does not support WebGL hardware acceleration. Please switch to the accessible 2D workstations view.
        </p>
        {onSwitchToTableView && (
          <Button size="sm" onClick={onSwitchToTableView}>
            Switch to 2D Workstations
          </Button>
        )}
      </div>
    );
  }

  return (
    <ThreeErrorBoundary
      fallback={
        <div className="w-full h-[320px] rounded-xl border border-border bg-surface p-6 flex flex-col items-center justify-center text-center">
          <AlertCircle className="h-8 w-8 text-muted-foreground mb-2" />
          <h3 className="text-sm font-semibold text-foreground mb-1">
            Spatial View Fallback
          </h3>
          <p className="text-xs text-muted-foreground max-w-sm mb-4">
            Could not initialize 3D scene. You can view all agent assignments and workstations in the 2D panel below.
          </p>
          {onSwitchToTableView && (
            <Button size="sm" onClick={onSwitchToTableView}>
              View Workstations
            </Button>
          )}
        </div>
      }
    >
      <DynamicThreeCanvas
        employees={employees}
        workstations={workstations}
        selectedRole={selectedRole}
        onSelectRole={onSelectRole}
      />
    </ThreeErrorBoundary>
  );
}
