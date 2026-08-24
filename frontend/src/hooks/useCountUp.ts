import { useEffect, useRef, useState } from 'react';

/** Design plan's signature element: RadialRing.tsx's arc and its center
 * number sweep/count up together, in sync, on real data load. Two small
 * hooks make that work without changing RadialRing itself (kept
 * general-purpose, unaffected for any future non-animated caller):
 *
 * - useCountUp drives the NUMBER, via requestAnimationFrame, ease-out
 *   cubic. It never shows a placeholder or fabricated value -- it only
 *   animates the visual PATH to a number that was already fetched from
 *   the real API response, and always settles on that exact value.
 * - useSweepInOnMount gives RadialRing's own existing CSS transition
 *   (stroke-dashoffset, 300ms ease-out) something to animate on first
 *   paint. A value set on the very first render of a freshly-mounted DOM
 *   node does NOT trigger a CSS transition (only a later state change
 *   does) -- this hook renders 0 for one frame, then flips to the real
 *   percent one tick later via requestAnimationFrame, which the existing
 *   transition then animates smoothly. Subsequent value changes (e.g. a
 *   refetch landing a different number) are unaffected -- they update
 *   directly and still get the same smooth CSS transition, no
 *   unwanted reset back to zero first.
 *
 * Both respect prefers-reduced-motion by jumping straight to the real
 * value with no animation.
 */

function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export function useCountUp(value: number, durationMs = 350): number {
  const [display, setDisplay] = useState(0);
  const fromRef = useRef(0);
  const hasAnimatedOnceRef = useRef(false);

  useEffect(() => {
    if (prefersReducedMotion()) {
      setDisplay(value);
      fromRef.current = value;
      return;
    }

    const from = hasAnimatedOnceRef.current ? fromRef.current : 0;
    hasAnimatedOnceRef.current = true;
    if (from === value) {
      setDisplay(value);
      return;
    }

    const start = performance.now();
    let raf: number;
    const step = (now: number) => {
      const elapsed = now - start;
      const t = Math.min(1, elapsed / durationMs);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplay(from + (value - from) * eased);
      if (t < 1) {
        raf = requestAnimationFrame(step);
      } else {
        fromRef.current = value;
        setDisplay(value); // guarantee the exact real number on settle, not a rounded-eased approximation
      }
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return display;
}

export function useSweepInOnMount(targetPercent: number): number {
  const [percent, setPercent] = useState(0);
  const hasMountedRef = useRef(false);

  useEffect(() => {
    if (prefersReducedMotion() || hasMountedRef.current) {
      setPercent(targetPercent);
      hasMountedRef.current = true;
      return;
    }
    const raf = requestAnimationFrame(() => {
      setPercent(targetPercent);
      hasMountedRef.current = true;
    });
    return () => cancelAnimationFrame(raf);
  }, [targetPercent]);

  return percent;
}
