import * as React from 'react';
import { Skeleton } from './skeleton';
import { EmptyState } from './empty-state';
import { cn } from '@/lib/utils';

export interface ColumnDef<T> {
  id?: string;
  header: React.ReactNode;
  accessorKey?: keyof T;
  cell?: (item: T, index: number) => React.ReactNode;
  className?: string;
  headerClassName?: string;
}

export interface DataTableProps<T> {
  columns: ColumnDef<T>[];
  data: T[];
  keyExtractor: (item: T, index: number) => string;
  isLoading?: boolean;
  loadingRowCount?: number;
  emptyState?: React.ReactNode;
  errorState?: React.ReactNode;
  caption?: string;
  className?: string;
}

export function DataTable<T>({
  columns,
  data,
  keyExtractor,
  isLoading = false,
  loadingRowCount = 4,
  emptyState,
  errorState,
  caption,
  className,
}: DataTableProps<T>) {
  return (
    <div
      className={cn(
        'w-full overflow-x-auto rounded border border-border bg-surface',
        className
      )}
    >
      <table className="w-full text-left text-xs border-collapse">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead>
          <tr className="border-b border-border bg-surface-raised/60 text-muted-foreground">
            {columns.map((col, idx) => (
              <th
                key={col.id || String(col.accessorKey) || idx}
                scope="col"
                className={cn(
                  'h-9 px-3.5 py-2 text-left font-medium text-[11px] uppercase tracking-wider',
                  col.headerClassName
                )}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border/60">
          {errorState ? (
            <tr>
              <td colSpan={columns.length} className="p-6">
                {errorState}
              </td>
            </tr>
          ) : isLoading ? (
            Array.from({ length: loadingRowCount }).map((_, rIdx) => (
              <tr key={`loading-row-${rIdx}`} className="h-10">
                {columns.map((col, cIdx) => (
                  <td key={`loading-cell-${rIdx}-${cIdx}`} className="px-3.5 py-2.5">
                    <Skeleton className="h-4 w-full max-w-[140px]" />
                  </td>
                ))}
              </tr>
            ))
          ) : data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="p-8">
                {emptyState || (
                  <EmptyState
                    title="No records found"
                    description="There is no data to display at this time."
                  />
                )}
              </td>
            </tr>
          ) : (
            data.map((item, rowIdx) => {
              const rowKey = keyExtractor(item, rowIdx);
              return (
                <tr
                  key={rowKey}
                  className="transition-colors hover:bg-surface-raised/40 focus-within:bg-surface-raised/40"
                >
                  {columns.map((col, colIdx) => {
                    const cellContent = col.cell
                      ? col.cell(item, rowIdx)
                      : col.accessorKey
                      ? String(item[col.accessorKey] ?? '')
                      : null;

                    return (
                      <td
                        key={`${rowKey}-${col.id || String(col.accessorKey) || colIdx}`}
                        className={cn('px-3.5 py-2.5 align-middle text-foreground', col.className)}
                      >
                        {cellContent}
                      </td>
                    );
                  })}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
