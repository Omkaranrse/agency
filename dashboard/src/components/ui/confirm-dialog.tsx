'use client';

import * as React from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { X, AlertTriangle } from 'lucide-react';
import { Button } from './button';
import { cn } from '@/lib/utils';

export interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  isDestructive?: boolean;
  isLoading?: boolean;
  onConfirm: () => void | Promise<void>;
  children?: React.ReactNode;
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  isDestructive = false,
  isLoading = false,
  onConfirm,
  children,
}: ConfirmDialogProps) {
  const handleConfirm = async () => {
    await onConfirm();
  };

  return (
    <Dialog.Root open={open} onOpenChange={isLoading ? undefined : onOpenChange}>
      {children && <Dialog.Trigger asChild>{children}</Dialog.Trigger>}
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <Dialog.Content
          className={cn(
            'fixed left-[50%] top-[50%] z-50 grid w-full max-w-md translate-x-[-50%] translate-y-[-50%] gap-4 border border-border bg-surface p-5 shadow-lg duration-200 rounded sm:rounded',
            'focus:outline-none'
          )}
          onEscapeKeyDown={(e) => {
            if (isLoading) e.preventDefault();
          }}
          onPointerDownOutside={(e) => {
            if (isLoading) e.preventDefault();
          }}
        >
          <div className="flex items-start gap-3">
            {isDestructive && (
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded bg-danger-surface border border-danger/30 text-danger mt-0.5">
                <AlertTriangle className="h-4 w-4" aria-hidden="true" />
              </div>
            )}
            <div className="flex-1 space-y-1">
              <Dialog.Title className="text-sm font-semibold text-foreground">
                {title}
              </Dialog.Title>
              <Dialog.Description className="text-xs text-muted-foreground leading-normal">
                {description}
              </Dialog.Description>
            </div>
            <Dialog.Close asChild disabled={isLoading}>
              <button
                type="button"
                className="rounded p-1 text-muted-foreground hover:text-foreground hover:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                aria-label="Close dialog"
              >
                <X className="h-4 w-4" />
              </button>
            </Dialog.Close>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-border/60">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={isLoading}
              onClick={() => onOpenChange(false)}
            >
              {cancelLabel}
            </Button>
            <Button
              type="button"
              variant={isDestructive ? 'destructive' : 'primary'}
              size="sm"
              isLoading={isLoading}
              onClick={handleConfirm}
            >
              {confirmLabel}
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
