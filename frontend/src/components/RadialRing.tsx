import type { ReactNode } from 'react';

interface RadialRingProps {
  /** 0-100. */
  percent: number;
  /** Real data-semantic color (e.g. getRiskTierColor(mode)[tier]) --
   * never a hardcoded value. The ring's arc always shows the real
   * backend-provided severity -- it can never disagree with the actual
   * decision because it never invents its own color. */
  color: string;
  size?: number;
  strokeWidth?: number;
  /** Centered label, e.g. "86.35%" -- rendered in tabular mono by the caller. */
  label: ReactNode;
}

/** Radial progress ring -- the hero-stat treatment for a single
 * value-of-whole metric (fraud probability, HIGH-tier rate). Reserved
 * for exactly the few places a hero-sized single value genuinely fits;
 * dense table rows keep the horizontal RiskMeter and the confusion-
 * matrix/metric-grid pages stay plain cards -- not every number becomes
 * a ring.
 */
export function RadialRing({ percent, color, size = 96, strokeWidth = 8, label }: RadialRingProps) {
  const clamped = Math.max(0, Math.min(100, percent));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - clamped / 100);

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--color-bg-surface-raised)" strokeWidth={strokeWidth} />
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
          style={{
            transition: 'stroke-dashoffset 420ms cubic-bezier(0.22, 1, 0.36, 1)',
            filter: `drop-shadow(0 0 6px ${color}66)`,
          }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">{label}</div>
    </div>
  );
}
