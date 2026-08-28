import {
  DECISION_LEVEL,
  DRIFT_STATUS_LEVEL,
  RISK_TIER_LEVEL,
  SEVERITY_LEVEL,
  getLevelColor,
  getLevelTextColor,
} from '../theme/colors';
import type { SignalLevel } from '../theme/colors';
import { useThemeMode } from '../theme/ThemeProvider';
import type { AlertSeverity, Decision, DriftStatus, RiskTier } from '../types/api';

/** Every status badge in the app resolves through this one component and
 * the shared low/medium/high SignalLevel scale (see theme/colors.ts) --
 * LOW now genuinely gets the reserved accent gold (a reversal from the
 * prior monochrome system, where low/medium stayed uncolored). Dot fill +
 * border always use the raw level color (graphical, 3:1 threshold); the
 * LABEL TEXT uses getLevelTextColor, which in light mode substitutes
 * textPrimary for LOW specifically -- raw accent gold only clears 3.25:1
 * on white, short of the 4.5:1 text threshold, and the spec's hard rule
 * keeps accent out of small body text in light mode. Dark mode has no
 * such restriction (accent clears 5.7:1 there), so LOW's text stays gold
 * in dark mode -- the distinction is per-mode, not per-level.
 */
export function StatusBadge({ label, level }: { label: string; level: SignalLevel }) {
  const mode = useThemeMode();
  const fillColor = getLevelColor(mode, level);
  const textColor = getLevelTextColor(mode, level);
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium"
      style={{ color: textColor, borderColor: `${fillColor}55`, backgroundColor: `${fillColor}14` }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: fillColor }} />
      {label}
    </span>
  );
}

export function RiskTierBadge({ tier }: { tier: RiskTier }) {
  return <StatusBadge label={tier} level={RISK_TIER_LEVEL[tier]} />;
}

export function DecisionBadge({ decision }: { decision: Decision }) {
  return <StatusBadge label={decision} level={DECISION_LEVEL[decision]} />;
}

export function SeverityBadge({ severity }: { severity: AlertSeverity }) {
  return <StatusBadge label={severity} level={SEVERITY_LEVEL[severity]} />;
}

/** "Flagged in advance" is good news (the model already caught it) ->
 * low. "Not flagged" is the honest missed case -> high, the one place on
 * this badge the reserved rose is genuinely earned (a real missed-fraud
 * case deserves it). `hasData=false` means there was no prior prediction
 * record at all -- rendered with the plain muted tone directly, no level
 * applies since it isn't a risk reading at all. */
export function FlaggedInAdvanceBadge({ flagged, hasData }: { flagged: boolean; hasData: boolean }) {
  if (!hasData) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-0.5 text-xs font-normal text-text-muted">
        <span className="h-1.5 w-1.5 rounded-full border border-text-muted" />
        No prior risk data
      </span>
    );
  }
  return flagged ? <StatusBadge label="Flagged in advance" level="low" /> : <StatusBadge label="Not flagged" level="high" />;
}

/** Same 3-level system as risk tier/decision, applied to Tier 3B's drift
 * status -- STABLE->low, MODERATE_DRIFT->medium, SIGNIFICANT_DRIFT->high.
 * See src/monitoring/drift_detector.py for what these mean. */
const DRIFT_STATUS_LABEL: Record<DriftStatus, string> = {
  STABLE: 'Stable',
  MODERATE_DRIFT: 'Moderate drift',
  SIGNIFICANT_DRIFT: 'Significant drift',
};

export function DriftStatusBadge({ status }: { status: DriftStatus }) {
  return <StatusBadge label={DRIFT_STATUS_LABEL[status]} level={DRIFT_STATUS_LEVEL[status]} />;
}

/** Filled-checkmark treatment for a genuinely completed/passed state
 * (Submission Mapping's "Met"/"Built" rows) -- LOW-level color (good
 * news, quietest reading on the scale), but with a filled check icon
 * instead of the plain dot, distinct enough from a routine LOW badge that
 * it reads as an affirmative checklist mark rather than a risk rating. */
export function SuccessBadge({ label }: { label: string }) {
  const mode = useThemeMode();
  const fillColor = getLevelColor(mode, 'low');
  const textColor = getLevelTextColor(mode, 'low');
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium"
      style={{ color: textColor, borderColor: `${fillColor}55`, backgroundColor: `${fillColor}14` }}
    >
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
        <circle cx="6" cy="6" r="5.25" fill={fillColor} />
        <path d="M3.5 6.2 5.2 7.9 8.5 4.3" stroke="var(--color-bg-surface)" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {label}
    </span>
  );
}
