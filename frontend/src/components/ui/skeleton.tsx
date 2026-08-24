import type { ComponentProps } from 'react';
import { cn } from '../../lib/utils';

/** One canonical loading-placeholder primitive, replacing the N slightly
 * different hand-rolled `animate-pulse` divs that previously existed
 * per-page -- guarantees identical pulse timing/opacity everywhere
 * rather than each page's skeleton drifting slightly from the others.
 * Gentle pulse only (no shimmer-sweep -- shimmer reads as more
 * consumer-app than this tool's restrained motion language calls for).
 */
export function Skeleton({ className, ...props }: ComponentProps<'div'>) {
  return (
    <div
      className={cn('animate-pulse rounded-(--radius-card) border border-border bg-bg-surface-raised', className)}
      {...props}
    />
  );
}
