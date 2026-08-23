import type { ReactNode } from 'react';

interface RadialRingProps {
  /** 0-100. */
  percent: number;
  /** Real data-semantic color (e.g. RISK_TIER_COLOR[tier]) -- never a
   * hardcoded violet. See the design plan: the ring's arc always shows
   * the real backend-provided severity, exactly like the bar-form
   * RiskMeter it replaces on hero stats -- it can never disagree with
   * the actual decision because it never invents its own color.
   */
  color: string;
  size?: number;
  strokeWidth?: number;
  /** Centered label, e.g. "86.35%" -- rendered in tabular mono by the caller. */
  label: ReactNode;
}

/** Radial progress ring -- the hero-stat treatment for a single
 * value-of-whole metric (fraud probability, HIGH-tier rate). Reserved
 * for exactly the few places a hero-sized single value genuinely fits;
 * dense table rows keep the horizontal RiskMeter (see that component's
 * own docstring) and the confusion-matrix/metric-grid pages stay plain
 * cards -- not every number becomes a ring. Glow is intentionally
 * restrained (drop-shadow at low opacity, not a bright bloom) -- see
 * the design plan's self-critique on staying "serious tool."
 */
export function RadialRing({ percent, color, size = 96, strokeWidth = 8, label }: RadialRingProps) {
  const clamped = Math.max(0, Math.min(100, percent));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - clamped / 100);

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--color-bg-surface-raised)"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ filter: `drop-shadow(0 0 5px ${color}80)`, transition: 'stroke-dashoffset 300ms ease-out' }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">{label}</div>
    </div>
  );
}
