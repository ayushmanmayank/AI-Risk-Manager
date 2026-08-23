import { RISK_TIER_COLOR } from '../theme/colors';
import type { RiskTier } from '../types/api';

interface RiskMeterProps {
  probability: number;
  tier: RiskTier;
  /** Compact: inline table-cell use (High-Risk Transactions rows).
   * Default: a larger hero treatment (Transaction Detail, Chargeback evidence). */
  compact?: boolean;
}

// Purely visual reference marks -- these mirror src/risk/decision_engine.py's
// DEFAULT_MEDIUM_THRESHOLD/DEFAULT_HIGH_THRESHOLD as of this redesign, but
// this component never recomputes a tier from them: the fill color always
// comes from the real `tier` prop (the backend's actual decision), so a
// future threshold change can only make these two tick marks slightly
// stale-looking -- it can never make the meter show the wrong tier.
const MEDIUM_THRESHOLD_PERCENT = 30;
const HIGH_THRESHOLD_PERCENT = 70;

/** The signature visual element of this redesign: a horizontal probability
 * bar, tier-colored (single source of truth: RISK_TIER_COLOR, the same
 * constant every badge and chart already uses), with the exact percentage
 * in tabular mono type. Tick marks at the real decision-tier boundaries
 * let an analyst see at a glance not just "how risky" but "how close to
 * flipping tiers" -- this is why it's more than a generic progress bar.
 */
export function RiskMeter({ probability, tier, compact = false }: RiskMeterProps) {
  const fillPercent = Math.max(0, Math.min(100, probability * 100));
  const color = RISK_TIER_COLOR[tier];

  return (
    <div className={`flex items-center gap-3 ${compact ? 'min-w-[140px]' : 'min-w-[220px]'}`}>
      <div
        className="relative flex-1 overflow-hidden rounded-full bg-bg-surface-raised"
        style={{ height: compact ? 6 : 10 }}
      >
        <div
          className="absolute top-0 left-0 h-full rounded-full transition-[width] duration-300 ease-out"
          style={{ width: `${fillPercent}%`, backgroundColor: color }}
        />
        {/* Tier-boundary reference ticks -- see MEDIUM/HIGH_THRESHOLD_PERCENT above */}
        <div
          className="absolute top-0 h-full w-px bg-bg-base/60"
          style={{ left: `${MEDIUM_THRESHOLD_PERCENT}%` }}
        />
        <div
          className="absolute top-0 h-full w-px bg-bg-base/60"
          style={{ left: `${HIGH_THRESHOLD_PERCENT}%` }}
        />
      </div>
      <span
        className={`shrink-0 font-mono tabular-nums ${compact ? 'text-xs' : 'text-sm font-medium'}`}
        style={{ color }}
      >
        {(probability * 100).toFixed(2)}%
      </span>
    </div>
  );
}
