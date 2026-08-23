import { DECISION_COLOR, RISK_TIER_COLOR, SEVERITY_COLOR, TEXT_MUTED } from '../theme/colors';
import type { AlertSeverity, Decision, RiskTier } from '../types/api';

function StatusBadge({ label, color }: { label: string; color: string }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium"
      style={{ backgroundColor: `${color}1a`, color }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
}

export function RiskTierBadge({ tier }: { tier: RiskTier }) {
  return <StatusBadge label={tier} color={RISK_TIER_COLOR[tier]} />;
}

export function DecisionBadge({ decision }: { decision: Decision }) {
  return <StatusBadge label={decision} color={DECISION_COLOR[decision]} />;
}

export function SeverityBadge({ severity }: { severity: AlertSeverity }) {
  return <StatusBadge label={severity} color={SEVERITY_COLOR[severity]} />;
}

/** Reuses the same status colors as everywhere else: "flagged in advance"
 * is good news (the model already caught it) -> green; "not flagged" is
 * the honest missed case -> red. `hasData=false` means there was no prior
 * prediction record at all -- distinct from either flagged state.
 */
export function FlaggedInAdvanceBadge({ flagged, hasData }: { flagged: boolean; hasData: boolean }) {
  if (!hasData) {
    return <StatusBadge label="No prior risk data" color={TEXT_MUTED} />;
  }
  return flagged
    ? <StatusBadge label="Flagged in advance" color={SEVERITY_COLOR.NONE} />
    : <StatusBadge label="Not flagged" color={SEVERITY_COLOR.HIGH} />;
}
