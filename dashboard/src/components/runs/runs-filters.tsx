'use client';

import * as React from 'react';
import { Search, X, Filter } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { RunState } from '@/features/runs/types';

export interface RunsFiltersProps {
  search: string;
  onSearchChange: (value: string) => void;
  status: RunState | undefined;
  onStatusChange: (status: RunState | undefined) => void;
  onReset: () => void;
  isFiltered: boolean;
}

const ALL_STATUS_OPTIONS: { label: string; value: RunState }[] = [
  { label: 'Created', value: RunState.CREATED },
  { label: 'Planning', value: RunState.PLANNING },
  { label: 'Prototyping', value: RunState.PROTOTYPING },
  { label: 'Awaiting Approval', value: RunState.AWAITING_APPROVAL },
  { label: 'Building', value: RunState.BUILDING },
  { label: 'Testing', value: RunState.TESTING },
  { label: 'Deploying', value: RunState.DEPLOYING },
  { label: 'Completed', value: RunState.COMPLETED },
  { label: 'Failed', value: RunState.FAILED },
  { label: 'Cancelled', value: RunState.CANCELLED },
];

export function RunsFilters({
  search,
  onSearchChange,
  status,
  onStatusChange,
  onReset,
  isFiltered,
}: RunsFiltersProps) {
  return (
    <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 rounded border border-border bg-surface">
      <div className="flex flex-1 flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
        {/* Search input */}
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
          <Input
            placeholder="Search by project or run ID..."
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-8 h-8 text-xs"
            aria-label="Search runs"
          />
          {search && (
            <button
              type="button"
              onClick={() => onSearchChange('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              aria-label="Clear search"
            >
              <X className="h-3 w-3" />
            </button>
          )}
        </div>

        {/* Status filter dropdown */}
        <div className="w-full sm:w-48">
          <Select
            value={status || ''}
            onChange={(e) => {
              const val = e.target.value as RunState;
              onStatusChange(val ? val : undefined);
            }}
            aria-label="Filter runs by status"
          >
            <option value="">All Statuses</option>
            {ALL_STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </Select>
        </div>
      </div>

      {isFiltered && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onReset}
          className="text-xs text-muted-foreground hover:text-foreground self-end sm:self-auto"
        >
          <X className="h-3 w-3 mr-1" />
          <span>Reset filters</span>
        </Button>
      )}
    </div>
  );
}
