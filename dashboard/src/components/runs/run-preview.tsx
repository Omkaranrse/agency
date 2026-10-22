'use client';

import * as React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ExternalLink,
  Laptop,
  Smartphone,
  RefreshCw,
  EyeOff,
  AlertCircle,
  Lock,
  Maximize2,
  Minimize2,
  Sparkles,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ShimmerButton } from '@/components/framer/shimmer-button';
import { TextScramble } from '@/components/framer/text-scramble';

export interface RunPreviewProps {
  previewUrl: string | null | undefined;
  status: string;
  currentStage: string;
  isMaximized?: boolean;
  onToggleMaximize?: () => void;
}

export function RunPreview({
  previewUrl,
  status,
  currentStage,
  isMaximized = false,
  onToggleMaximize,
}: RunPreviewProps) {
  const [viewport, setViewport] = React.useState<'desktop' | 'mobile'>('desktop');
  const [iframeKey, setIframeKey] = React.useState(0);
  const [iframeLoading, setIframeLoading] = React.useState(true);
  const [embedBlocked, setEmbedBlocked] = React.useState(false);

  React.useEffect(() => {
    setIframeLoading(true);
    setEmbedBlocked(false);
  }, [previewUrl]);

  // Validate URL format (only allow http / https)
  const isValidUrl = React.useMemo(() => {
    if (!previewUrl) return false;
    try {
      const parsed = new URL(previewUrl);
      return parsed.protocol === 'http:' || parsed.protocol === 'https:';
    } catch {
      return false;
    }
  }, [previewUrl]);

  const handleReload = () => {
    setIframeLoading(true);
    setEmbedBlocked(false);
    setIframeKey((k) => k + 1);
  };

  return (
    <div className="flex flex-col h-full rounded-xl border border-border bg-surface/80 backdrop-blur-sm overflow-hidden shadow-sm">
      {/* Futuristic Browser Chrome Toolbar */}
      <div className="flex items-center justify-between px-3.5 py-2.5 border-b border-border bg-surface-raised/60">
        <div className="flex items-center gap-3">
          {/* Simulated traffic light dots */}
          <div className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-error/70 border border-error" />
            <span className="h-2.5 w-2.5 rounded-full bg-warning/70 border border-warning" />
            <span className="h-2.5 w-2.5 rounded-full bg-success/70 border border-success" />
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-foreground tracking-wider uppercase font-mono">
              Live Preview
            </span>
          </div>
        </div>

        {/* Center: Address Bar */}
        {isValidUrl ? (
          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-md bg-background/80 border border-border/80 text-[11px] font-mono text-muted-foreground max-w-xs truncate">
            <Lock className="h-3 w-3 text-brand-teal shrink-0" />
            <span className="truncate">{previewUrl}</span>
          </div>
        ) : (
          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-md bg-background/40 border border-border/40 text-[10px] font-mono text-muted-foreground">
            <span>SANDBOX VIEWPORT</span>
          </div>
        )}

        {/* Viewport controls & actions */}
        <div className="flex items-center gap-1.5">
          <div className="inline-flex rounded-lg border border-border p-0.5 bg-background text-muted-foreground">
            <button
              type="button"
              onClick={() => setViewport('desktop')}
              className={`p-1.5 rounded transition-all ${
                viewport === 'desktop'
                  ? 'bg-surface-raised text-brand-teal font-medium shadow-sm'
                  : 'hover:text-foreground'
              }`}
              title="Desktop Viewport"
              aria-label="Desktop Viewport"
            >
              <Laptop className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setViewport('mobile')}
              className={`p-1.5 rounded transition-all ${
                viewport === 'mobile'
                  ? 'bg-surface-raised text-brand-teal font-medium shadow-sm'
                  : 'hover:text-foreground'
              }`}
              title="Mobile Device (375px)"
              aria-label="Mobile Device (375px)"
            >
              <Smartphone className="h-3.5 w-3.5" />
            </button>
          </div>

          {isValidUrl && (
            <>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={handleReload}
                title="Reload Preview"
                aria-label="Reload Preview"
                className="hover:text-brand-teal"
              >
                <RefreshCw className={`h-3 w-3 ${iframeLoading ? 'animate-spin text-brand-teal' : ''}`} />
              </Button>

              {onToggleMaximize && (
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={onToggleMaximize}
                  title={isMaximized ? 'Restore View' : 'Maximize Preview (Focus Mode)'}
                  aria-label={isMaximized ? 'Restore View' : 'Maximize Preview (Focus Mode)'}
                  className="hover:text-brand-teal"
                >
                  {isMaximized ? (
                    <Minimize2 className="h-3.5 w-3.5" />
                  ) : (
                    <Maximize2 className="h-3.5 w-3.5" />
                  )}
                </Button>
              )}

              <ShimmerButton asChild size="sm" variant="outline" className="h-7 text-[11px] px-2.5">
                <a
                  href={previewUrl!}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1"
                >
                  <span>Launch</span>
                  <ExternalLink className="h-3 w-3" />
                </a>
              </ShimmerButton>
            </>
          )}
        </div>
      </div>

      {/* Frame Container */}
      <div className="relative flex-1 bg-background/60 p-4 overflow-auto flex items-center justify-center min-h-[460px]">
        {!isValidUrl ? (
          <div className="flex flex-col items-center justify-center text-center p-8 text-muted-foreground max-w-sm">
            <div className="relative mb-4">
              <div className="h-14 w-14 rounded-xl bg-surface-raised border border-border flex items-center justify-center text-brand-teal">
                <EyeOff className="h-6 w-6 opacity-70" />
              </div>
              <span className="absolute -top-1 -right-1 flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-teal opacity-75" />
                <span className="relative inline-flex rounded-full h-3 w-3 bg-brand-teal" />
              </span>
            </div>

            <h3 className="text-sm font-semibold text-foreground mb-1.5">
              Preview Not Available Yet
            </h3>
            <p className="text-xs leading-relaxed text-muted-foreground mb-4">
              The Designer & Builder agents are currently generating the layout. Once ready, the live sandboxed prototype will automatically render here.
            </p>
            <div className="text-[11px] font-mono border border-border bg-surface px-3 py-1.5 rounded-lg text-muted-foreground">
              Current stage: <span className="text-brand-teal font-semibold uppercase">{currentStage}</span>
            </div>
          </div>
        ) : embedBlocked ? (
          <div className="flex flex-col items-center justify-center text-center p-8 text-muted-foreground max-w-sm">
            <AlertCircle className="h-10 w-10 mb-3 text-warning" />
            <h3 className="text-sm font-semibold text-foreground mb-1">
              Embedding Restricted by Host
            </h3>
            <p className="text-xs leading-relaxed mb-4 text-muted-foreground">
              The sandboxed origin header restricted inline iframe rendering. You can view the live interactive prototype directly in an isolated browser window.
            </p>
            <ShimmerButton asChild size="sm">
              <a
                href={previewUrl!}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5"
              >
                <span>Open in Isolated Window</span>
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </ShimmerButton>
          </div>
        ) : (
          <motion.div
            layout
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
            className={`transition-all duration-300 relative ${
              viewport === 'mobile'
                ? 'w-[375px] h-[667px] shadow-2xl border-4 border-border/80 rounded-[32px] overflow-hidden bg-black ring-1 ring-border'
                : 'w-full h-full min-h-[440px] rounded-lg overflow-hidden border border-border/60 shadow-inner'
            }`}
          >
            {/* Mobile device notch simulation */}
            {viewport === 'mobile' && (
              <div className="absolute top-0 left-1/2 -translate-x-1/2 h-5 w-28 bg-border/90 rounded-b-xl z-20 flex items-center justify-center">
                <span className="h-2 w-2 rounded-full bg-background/80 mr-2" />
                <span className="h-1.5 w-8 rounded-full bg-background/50" />
              </div>
            )}

            {iframeLoading && (
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-surface/80 backdrop-blur-sm z-10 gap-2">
                <RefreshCw className="h-6 w-6 animate-spin text-brand-teal" />
                <span className="font-mono text-xs text-muted-foreground">
                  Synchronizing sandbox DOM...
                </span>
              </div>
            )}
            <iframe
              key={iframeKey}
              src={previewUrl!}
              title="Website prototype preview"
              className="w-full h-full border-0 bg-white"
              sandbox="allow-scripts allow-same-origin allow-forms"
              onLoad={() => setIframeLoading(false)}
              onError={() => {
                setIframeLoading(false);
                setEmbedBlocked(true);
              }}
            />
          </motion.div>
        )}
      </div>
    </div>
  );
}
