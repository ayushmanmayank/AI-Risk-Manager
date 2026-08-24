import {
  DECISION_LEVEL,
  RISK_TIER_LEVEL,
  SEVERITY_LEVEL,
  SIGNAL_LEVEL_COLOR,
  SIGNAL_LEVEL_COLOR_ON_DARK,
  TEXT_MUTED,
  TEXT_MUTED_ON_DARK,
} from '../theme/colors';
import type { SignalLevel } from '../theme/colors';
import type { AlertSeverity, Decision, DriftStatus, RiskTier } from '../types/api';

/** The form-over-color system this whole re-theme is built around (see
 * theme/colors.ts's top-of-file docstring): quiet/noted/alert each get a
 * genuinely different VISUAL FORM, not just a duller shade of the same
 * treatment --
 *   quiet: outline dot, normal weight, no background tint
 *   noted: filled dot, medium weight, a faint neutral tint
 *   alert: filled dot, semibold weight, the accent's own tint -- the
 *          only level that also changes hue
 * This is what makes LOW vs. MEDIUM legible at a glance without a second
 * competing color -- the dot fill and font weight ARE the distinction.
 */
export function StatusBadge({
  label,
  level,
  onDark = false,
}: {
  label: string;
  level: SignalLevel;
  /** True when this badge renders on a card-dark/card-dense-dark surface.
   * The level color is a raw hex value passed via inline `style`, not a
   * CSS var(), so it doesn't pick up the card's cascade trick -- it needs
   * its own on-dark lookup. See theme/colors.ts's SIGNAL_LEVEL_COLOR_ON_DARK
   * docstring for why this isn't optional polish: the light-surface
   * "noted" color is literally identical to the dark card background. */
  onDark?: boolean;
}) {
  const color = onDark ? SIGNAL_LEVEL_COLOR_ON_DARK[level] : SIGNAL_LEVEL_COLOR[level];
  const isQuiet = level === 'quiet';
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-(--radius-control) border px-2.5 py-0.5 text-xs ${
        isQuiet ? 'font-normal' : level === 'noted' ? 'font-medium' : 'font-semibold'
      }`}
      style={{
        color,
        borderColor: isQuiet ? 'var(--color-border)' : color,
        backgroundColor: isQuiet ? 'transparent' : `${color}14`,
      }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={
          isQuiet
            ? { border: `1px solid ${color}`, backgroundColor: 'transparent' }
            : { backgroundColor: color }
        }
      />
      {label}
    </span>
  );
}

export function RiskTierBadge({ tier, onDark = false }: { tier: RiskTier; onDark?: boolean }) {
  return <StatusBadge label={tier} level={RISK_TIER_LEVEL[tier]} onDark={onDark} />;
}

export function DecisionBadge({ decision, onDark = false }: { decision: Decision; onDark?: boolean }) {
  return <StatusBadge label={decision} level={DECISION_LEVEL[decision]} onDark={onDark} />;
}

export function SeverityBadge({ severity, onDark = false }: { severity: AlertSeverity; onDark?: boolean }) {
  return <StatusBadge label={severity} level={SEVERITY_LEVEL[severity]} onDark={onDark} />;
}

/** "Flagged in advance" is good news (the model already caught it) ->
 * quiet, same "silence is the signal" logic as everywhere else in this
 * system: a good outcome doesn't need to shout. "Not flagged" is the
 * honest missed case -> alert, the one place on this badge the reserved
 * accent is genuinely earned (a real missed-fraud case deserves it).
 * `hasData=false` means there was no prior prediction record at all --
 * distinct from either flagged state, rendered with the plain muted
 * color directly (no level applies -- it isn't a risk reading at all).
 */
export function FlaggedInAdvanceBadge({
  flagged,
  hasData,
  onDark = false,
}: {
  flagged: boolean;
  hasData: boolean;
  onDark?: boolean;
}) {
  if (!hasData) {
    const mutedColor = onDark ? TEXT_MUTED_ON_DARK : TEXT_MUTED;
    return (
      <span className="inline-flex items-center gap-1.5 rounded-(--radius-control) border border-border px-2.5 py-0.5 text-xs font-normal" style={{ color: mutedColor }}>
        <span className="h-1.5 w-1.5 rounded-full" style={{ border: `1px solid ${mutedColor}` }} />
        No prior risk data
      </span>
    );
  }
  return flagged
    ? <StatusBadge label="Flagged in advance" level="quiet" onDark={onDark} />
    : <StatusBadge label="Not flagged" level="alert" onDark={onDark} />;
}

/** Same 3-level system as risk tier/decision, applied to Tier 3B's drift
 * status -- STABLE->quiet, MODERATE_DRIFT->noted, SIGNIFICANT_DRIFT->
 * alert. See src/monitoring/drift_detector.py for what these mean. */
const DRIFT_STATUS_LABEL: Record<DriftStatus, string> = {
  STABLE: 'Stable',
  MODERATE_DRIFT: 'Moderate drift',
  SIGNIFICANT_DRIFT: 'Significant drift',
};

const DRIFT_STATUS_LEVEL: Record<DriftStatus, SignalLevel> = {
  STABLE: 'quiet',
  MODERATE_DRIFT: 'noted',
  SIGNIFICANT_DRIFT: 'alert',
};

/** Kept exported (DriftMonitor.tsx's per-feature bars read raw colors,
 * not badges) -- resolved from the same level map above, single source
 * of truth either way. */
export const DRIFT_STATUS_COLOR: Record<DriftStatus, string> = {
  STABLE: SIGNAL_LEVEL_COLOR[DRIFT_STATUS_LEVEL.STABLE],
  MODERATE_DRIFT: SIGNAL_LEVEL_COLOR[DRIFT_STATUS_LEVEL.MODERATE_DRIFT],
  SIGNIFICANT_DRIFT: SIGNAL_LEVEL_COLOR[DRIFT_STATUS_LEVEL.SIGNIFICANT_DRIFT],
};

/** DriftMonitor.tsx's per-feature bars now always render on its own
 * card-dark section, so this is the one raw-color map here without a
 * light-surface fallback still in use anywhere. */
export const DRIFT_STATUS_COLOR_ON_DARK: Record<DriftStatus, string> = {
  STABLE: SIGNAL_LEVEL_COLOR_ON_DARK[DRIFT_STATUS_LEVEL.STABLE],
  MODERATE_DRIFT: SIGNAL_LEVEL_COLOR_ON_DARK[DRIFT_STATUS_LEVEL.MODERATE_DRIFT],
  SIGNIFICANT_DRIFT: SIGNAL_LEVEL_COLOR_ON_DARK[DRIFT_STATUS_LEVEL.SIGNIFICANT_DRIFT],
};

export function DriftStatusBadge({ status, onDark = false }: { status: DriftStatus; onDark?: boolean }) {
  return <StatusBadge label={DRIFT_STATUS_LABEL[status]} level={DRIFT_STATUS_LEVEL[status]} onDark={onDark} />;
}
