/**
 * Fixed status palette (never themed) for risk-tier severity, taken from the
 * dataviz skill's validated reference palette (references/palette.md).
 * LOW -> good, MEDIUM -> warning, HIGH -> critical ("serious" unused: only
 * three risk tiers exist). Light-surface values only — Day 4 dashboard is
 * light-mode only by scope choice; revisit if dark mode is ever requested.
 */
export const RISK_TIER_COLOR: Record<'LOW' | 'MEDIUM' | 'HIGH', string> = {
  LOW: '#0ca30c',
  MEDIUM: '#fab219',
  HIGH: '#d03b3b',
};

/** Decisions map 1:1 to the same status severity as their risk tier
 * (ALLOW<-LOW, REVIEW<-MEDIUM, HOLD<-HIGH), so they reuse the same fixed
 * status palette rather than a separate categorical one.
 */
export const DECISION_COLOR: Record<'ALLOW' | 'REVIEW' | 'HOLD', string> = {
  ALLOW: '#0ca30c',
  REVIEW: '#fab219',
  HOLD: '#d03b3b',
};

/** Alert severity uses the full 4-step status palette (risk tier/decision
 * only need 3): NONE reads as "all clear" (good/green), through LOW,
 * MEDIUM, to HIGH (critical/red) -- see src/anomaly/spike_detector.py for
 * where these severities come from.
 */
export const SEVERITY_COLOR: Record<'NONE' | 'LOW' | 'MEDIUM' | 'HIGH', string> = {
  NONE: '#0ca30c',
  LOW: '#fab219',
  MEDIUM: '#ec835a',
  HIGH: '#d03b3b',
};

/** Categorical slots 1 & 2 from the dataviz skill's reference palette, in
 * fixed order (never cycled) -- used for the precision/recall curve,
 * the only 2-series chart in this app.
 */
export const SERIES_COLOR = {
  precision: '#2a78d6',
  recall: '#eb6834',
};

export const TEXT_PRIMARY = '#0b0b0b';
export const TEXT_SECONDARY = '#52514e';
export const TEXT_MUTED = '#898781';
export const GRIDLINE = '#e1e0d9';
export const CHART_SURFACE = '#fcfcfb';
