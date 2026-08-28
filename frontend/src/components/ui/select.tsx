import * as SelectPrimitive from '@radix-ui/react-select';
import type { ComponentProps } from 'react';
import { cn } from '../../lib/utils';

/** shadcn/ui's standard Select primitives (Radix underneath), restyled
 * to this app's tokens. Replaces the native <select> filter controls
 * (High-Risk Transactions) -- a native select's dropdown panel can't be
 * styled consistently across browsers/OSes, which made it impossible to
 * guarantee the explicit hover/active/focus states the Phase 4 detail
 * pass requires. No icon library added -- chevron/check are inline SVG,
 * consistent with the rest of this app (no icon dependency anywhere else
 * either).
 */

function Select(props: ComponentProps<typeof SelectPrimitive.Root>) {
  return <SelectPrimitive.Root {...props} />;
}

function SelectValue(props: ComponentProps<typeof SelectPrimitive.Value>) {
  return <SelectPrimitive.Value {...props} />;
}

function SelectTrigger({ className, children, ...props }: ComponentProps<typeof SelectPrimitive.Trigger>) {
  return (
    <SelectPrimitive.Trigger
      className={cn(
        'flex h-8 items-center justify-between gap-2 rounded-(--radius-control) border border-border bg-bg-surface px-2.5 text-sm text-text-primary outline-none',
        'transition-colors duration-150',
        'hover:bg-bg-surface-raised',
        'data-[state=open]:bg-bg-surface-raised data-[state=open]:border-accent',
        'focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2',
        'disabled:cursor-not-allowed disabled:opacity-50',
        className,
      )}
      {...props}
    >
      {children}
      <SelectPrimitive.Icon asChild>
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className="shrink-0 text-text-muted">
          <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  );
}

function SelectContent({ className, children, position = 'popper', ...props }: ComponentProps<typeof SelectPrimitive.Content>) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        position={position}
        className={cn(
          'popover-content z-50 min-w-32 overflow-hidden rounded-(--radius-control) border border-border bg-bg-surface-raised text-text-primary shadow-(--shadow-popover)',
          position === 'popper' && 'data-[side=bottom]:translate-y-1 data-[side=top]:-translate-y-1',
          className,
        )}
        {...props}
      >
        <SelectPrimitive.Viewport className="p-1">{children}</SelectPrimitive.Viewport>
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  );
}

function SelectItem({ className, children, ...props }: ComponentProps<typeof SelectPrimitive.Item>) {
  return (
    <SelectPrimitive.Item
      className={cn(
        'relative flex cursor-pointer select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-text-primary outline-none',
        'transition-colors duration-100',
        'data-highlighted:bg-bg-surface data-highlighted:text-text-primary',
        'data-disabled:pointer-events-none data-disabled:opacity-50',
        className,
      )}
      {...props}
    >
      <span className="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
        <SelectPrimitive.ItemIndicator>
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" style={{ color: 'var(--color-text-primary)' }}>
            <path d="M2.5 6.5L5 9L9.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </SelectPrimitive.ItemIndicator>
      </span>
      <SelectPrimitive.ItemText className="pl-5">{children}</SelectPrimitive.ItemText>
    </SelectPrimitive.Item>
  );
}

export { Select, SelectContent, SelectItem, SelectTrigger, SelectValue };
