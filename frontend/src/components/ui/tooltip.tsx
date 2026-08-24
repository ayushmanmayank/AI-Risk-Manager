import * as TooltipPrimitive from '@radix-ui/react-tooltip';
import type { ComponentProps } from 'react';
import { cn } from '../../lib/utils';

/** shadcn/ui's standard Tooltip primitives (Radix underneath), restyled
 * to this app's own tokens rather than shadcn's default zinc/slate
 * palette -- see the design plan: no installed component should look
 * visually foreign to the rest of the app. Used for SHAP feature rows
 * (Transaction/Chargeback Detail) to surface the raw contribution
 * magnitude on hover without cluttering the row itself.
 */

function TooltipProvider({ delayDuration = 150, ...props }: ComponentProps<typeof TooltipPrimitive.Provider>) {
  return <TooltipPrimitive.Provider delayDuration={delayDuration} {...props} />;
}

function Tooltip(props: ComponentProps<typeof TooltipPrimitive.Root>) {
  return (
    <TooltipProvider>
      <TooltipPrimitive.Root {...props} />
    </TooltipProvider>
  );
}

function TooltipTrigger(props: ComponentProps<typeof TooltipPrimitive.Trigger>) {
  return <TooltipPrimitive.Trigger {...props} />;
}

function TooltipContent({
  className,
  sideOffset = 6,
  children,
  ...props
}: ComponentProps<typeof TooltipPrimitive.Content>) {
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Content
        sideOffset={sideOffset}
        className={cn(
          // .tooltip-content (index.css) keys a sub-150ms fade+scale off
          // Radix's own data-state -- deliberately hand-written rather
          // than pulling in the tailwindcss-animate plugin for one
          // component's entrance transition. No bounce/elastic easing;
          // this app's motion language is restrained throughout.
          'tooltip-content z-50 rounded-(--radius-control) border border-border bg-bg-surface-raised px-2.5 py-1.5 font-sans text-xs text-text-primary shadow-(--shadow-popover)',
          className,
        )}
        {...props}
      >
        {children}
        <TooltipPrimitive.Arrow className="fill-bg-surface-raised" />
      </TooltipPrimitive.Content>
    </TooltipPrimitive.Portal>
  );
}

export { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger };
