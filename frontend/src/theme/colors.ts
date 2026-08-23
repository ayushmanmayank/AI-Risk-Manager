/**
 * Fixed status palette (never themed) for risk-tier severity -- see the
 * UI redesign's design plan (feature/ui-redesign) for the full reasoning.
 * LOW -> good, MEDIUM -> warning, HIGH -> critical ("serious" unused: only
 * three risk tiers exist). Dark-surface values -- matches src/index.css's
 * @theme block (--color-risk-low/medium/high) exactly; kept as a separate
 * JS-side export because Recharts/SVG props take raw color strings, not
 * Tailwind classes.
 */
export const RISK_TIER_COLOR: Record<'LOW' | 'MEDIUM' | 'HIGH', string> = {
  LOW: '#3fa66b',
  MEDIUM: '#db8a3f',
  HIGH: '#c75450',
};

/** Decisions map 1:1 to the same status severity as their risk tier
 * (ALLOW<-LOW, REVIEW<-MEDIUM, HOLD<-HIGH), so they reuse the same fixed
 * status palette rather than a separate categorical one.
 */
export const DECISION_COLOR: Record<'ALLOW' | 'REVIEW' | 'HOLD', string> = {
  ALLOW: '#3fa66b',
  REVIEW: '#db8a3f',
  HOLD: '#c75450',
};

/** Alert severity uses a 4-step scale (risk tier/decision only need 3):
 * NONE reads as "all clear" (good/green), through LOW (soft amber -- a
 * distinct fourth step, not just a dimmer MEDIUM), MEDIUM, to HIGH
 * (critical/red) -- see src/anomaly/spike_detector.py for where these
 * severities come from.
 */
export const SEVERITY_COLOR: Record<'NONE' | 'LOW' | 'MEDIUM' | 'HIGH', string> = {
  NONE: '#3fa66b',
  LOW: '#d4b24c',
  MEDIUM: '#db8a3f',
  HIGH: '#c75450',
};

/** Categorical slots 1 & 2, in fixed order (never cycled) -- used for the
 * precision/recall curve, the only 2-series chart in this app. Precision
 * (the "headline" metric this page is built around) gets the single
 * signal violet ACCENT below -- deliberately the only place on this
 * chart violet appears, so it keeps one meaning. Recall gets a distinct
 * neutral-blue that is neither violet nor a risk-tier color, so this
 * 2-series comparison never reads as if it were encoding risk severity.
 */
export const SERIES_COLOR = {
  precision: '#a78bfa',
  recall: '#7c8b9e',
};

/** Neutral, non-status color for "the norm"/baseline series (e.g. Fraud
 * Spike's baseline-vs-current bars) -- deliberately not any risk-tier or
 * accent color, since a baseline isn't a risk state.
 */
export const BASELINE_COLOR = '#5c5468';

/** The single signal-violet accent -- UI interaction/emphasis only
 * (nav active state, focus rings, links, "live" indicators, the
 * headline series above). NEVER used for risk severity -- see
 * RISK_TIER_COLOR/DECISION_COLOR/SEVERITY_COLOR above for that, kept as
 * a completely separate, unchanged color system on purpose.
 */
export const ACCENT = '#a78bfa';

export const TEXT_PRIMARY = '#edeef0';
export const TEXT_SECONDARY = '#9a94ac';
export const TEXT_MUTED = '#6b6478';
export const GRIDLINE = 'rgba(167, 139, 250, 0.12)';
export const CHART_SURFACE = '#17141f';
