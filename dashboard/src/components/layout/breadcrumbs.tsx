import * as React from 'react';
import Link from 'next/link';
import { ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export interface BreadcrumbsProps extends React.HTMLAttributes<HTMLElement> {
  items: BreadcrumbItem[];
}

export function Breadcrumbs({ items, className, ...props }: BreadcrumbsProps) {
  if (items.length === 0) return null;

  return (
    <nav aria-label="Breadcrumb" className={cn('flex items-center text-xs', className)} {...props}>
      <ol className="flex items-center gap-1.5 text-muted-foreground">
        {items.map((item, index) => {
          const isLast = index === items.length - 1;

          return (
            <React.Fragment key={`${item.label}-${index}`}>
              {index > 0 && (
                <li aria-hidden="true" className="text-border select-none">
                  <ChevronRight className="h-3 w-3" />
                </li>
              )}
              <li>
                {isLast || !item.href ? (
                  <span
                    className={cn(
                      'font-medium text-foreground',
                      isLast && 'truncate max-w-[200px] inline-block align-bottom'
                    )}
                    aria-current={isLast ? 'page' : undefined}
                  >
                    {item.label}
                  </span>
                ) : (
                  <Link
                    href={item.href}
                    className="hover:text-foreground transition-colors hover:underline underline-offset-2"
                  >
                    {item.label}
                  </Link>
                )}
              </li>
            </React.Fragment>
          );
        })}
      </ol>
    </nav>
  );
}
