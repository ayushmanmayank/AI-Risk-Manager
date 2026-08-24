/**
 * MONOCHROME/EDITORIAL RE-THEME (feature/ui-remake, design-direction
 * change) -- full replacement of the prior dark-violet-plus-4-status-hues
 * system. Grounded in three real references: Bloomberg Terminal ("color
 * is never decorative... reserved strictly for data, labels, and active
 * states"), Mercury (monochrome base, editorial serif headlines), and
 * Ramp (warm off-white canvas, ONE accent that appears only where money
 * moves). See the design-plan message for the full citation trail.
 *
 * THE CORE RULE: there is exactly ONE reserved accent color, and it means
 * exactly one thing -- HIGH risk / an active alert. Nowhere else. LOW and
 * MEDIUM are not "less saturated versions of a risk palette" -- they are
 * NOT COLORED AT ALL. They're differentiated by TYPE WEIGHT instead:
 *
 *   quiet  ("nothing to see")   -> --color-text-secondary (muted gray)
 *   noted  ("worth a glance")   -> --color-text-primary   (off-black --
 *                                   the same weight as any heading, so it
 *                                   visually "weighs more" than quiet
 *                                   without needing a second hue)
 *   alert  ("needs attention")  -> --color-accent          (the one signal)
 *
 * This is why RISK_TIER_COLOR/SEVERITY_COLOR below only ever resolve to
 * one of THREE values total, not a rainbow of per-tier hues like the
 * prior system had (decisions map onto the same three via DECISION_LEVEL,
 * but nothing renders a decision as a raw color, so there's no
 * DECISION_COLOR export -- see that map's own comment). Badge.tsx
 * additionally varies dot-fill and font-weight by level -- see
 * SIGNAL_LEVEL below -- so the distinction is genuinely encoded in form,
 * not just a duller color.
 */

export type SignalLevel = 'quiet' | 'noted' | 'alert';

export const TEXT_PRIMARY = '#16161a';
// Not exported -- no external call site needs the light-surface secondary
// color as a raw value anymore (the ones that used to have all moved to
// TEXT_SECONDARY_ON_DARK once their card went dark). Still needed here
// internally, as SIGNAL_LEVEL_COLOR/SERIES_COLOR's "quiet"/"recall" value.
const TEXT_SECONDARY = '#6e6b72';
export const TEXT_MUTED = '#9c98a0';

/** The one reserved accent -- HIGH risk / active alert, nowhere else in
 * the UI. Deliberately a warm SIGNAL-red, not an amber/gold "beacon"
 * color: this is a fraud tool, and HIGH has to unambiguously mean danger,
 * not just "notice me." See the design plan for the full reasoning
 * against the lighthouse-amber alternative. */
export const ACCENT = '#c4321e';

export const SIGNAL_LEVEL_COLOR: Record<SignalLevel, string> = {
  quiet: TEXT_SECONDARY,
  noted: TEXT_PRIMARY,
  alert: ACCENT,
};

export const RISK_TIER_LEVEL: Record<'LOW' | 'MEDIUM' | 'HIGH', SignalLevel> = {
  LOW: 'quiet',
  MEDIUM: 'noted',
  HIGH: 'alert',
};

/** Kept as Record<Tier, string> (not just Record<Tier, SignalLevel>) so
 * every existing call site that wants a raw color string -- RadialRing's
 * `color` prop, RiskMeter's fill, Recharts' `<Cell fill=...>` -- keeps
 * working with ZERO changes; only the VALUES changed, resolved from
 * SIGNAL_LEVEL_COLOR above so there is still exactly one source of truth
 * for what each level actually looks like. */
export const RISK_TIER_COLOR: Record<'LOW' | 'MEDIUM' | 'HIGH', string> = {
  LOW: SIGNAL_LEVEL_COLOR[RISK_TIER_LEVEL.LOW],
  MEDIUM: SIGNAL_LEVEL_COLOR[RISK_TIER_LEVEL.MEDIUM],
  HIGH: SIGNAL_LEVEL_COLOR[RISK_TIER_LEVEL.HIGH],
};

/** Decisions map 1:1 to the same status severity as their risk tier
 * (ALLOW<-LOW, REVIEW<-MEDIUM, HOLD<-HIGH), so they reuse the same level
 * system rather than a separate categorical one. */
export const DECISION_LEVEL: Record<'ALLOW' | 'REVIEW' | 'HOLD', SignalLevel> = {
  ALLOW: 'quiet',
  REVIEW: 'noted',
  HOLD: 'alert',
};
// No DECISION_COLOR (resolved-color) export here, unlike RISK_TIER_COLOR/
// SEVERITY_COLOR below -- nothing in the app renders a decision as a raw
// color value; DecisionBadge (Badge.tsx) reads DECISION_LEVEL directly.

/** Alert severity is a 4-step scale but there are only 3 form-levels.
 * NONE and LOW both fold into "quiet" (their own label text -- "NONE" vs
 * "LOW" -- already carries the distinction; z>=3.0-but-mild doesn't
 * warrant the same visual weight as a genuinely elevated MEDIUM/HIGH
 * reading) -- see src/anomaly/spike_detector.py for where these
 * severities come from. */
export const SEVERITY_LEVEL: Record<'NONE' | 'LOW' | 'MEDIUM' | 'HIGH', SignalLevel> = {
  NONE: 'quiet',
  LOW: 'quiet',
  MEDIUM: 'noted',
  HIGH: 'alert',
};
export const SEVERITY_COLOR: Record<'NONE' | 'LOW' | 'MEDIUM' | 'HIGH', string> = {
  NONE: SIGNAL_LEVEL_COLOR[SEVERITY_LEVEL.NONE],
  LOW: SIGNAL_LEVEL_COLOR[SEVERITY_LEVEL.LOW],
  MEDIUM: SIGNAL_LEVEL_COLOR[SEVERITY_LEVEL.MEDIUM],
  HIGH: SIGNAL_LEVEL_COLOR[SEVERITY_LEVEL.HIGH],
};

/** Precision/recall (Threshold Simulator) get ZERO accent -- this is
 * model-performance data, not risk-tier data, so the reserved signal
 * doesn't apply here at all (see the design plan's item 5). The two
 * series are differentiated by LINE STYLE (solid vs. dashed) in
 * PrecisionRecallCurveChart.tsx, not color -- these two values only need
 * to be distinguishable enough for the legend swatch/tooltip text, not
 * carry the whole distinction themselves. */
export const SERIES_COLOR = {
  precision: TEXT_PRIMARY,
  recall: TEXT_SECONDARY,
};

/** Neutral, non-status color for "the norm"/baseline series (e.g. Fraud
 * Spike's baseline-vs-current bars) -- a light-medium warm gray,
 * deliberately lighter than TEXT_SECONDARY so the "current" bar (colored
 * by severity level) reads as the one thing actually varying. */
export const BASELINE_COLOR = '#b5b1a8';

export const GRIDLINE = '#e2dfda';

/**
 * DARK-SURFACE VARIANT (nav/header + Dashboard's cards, per the specific
 * layout revision request) -- everything above this point assumes text
 * sits on the off-white canvas/off-white cards. These are the flipped
 * equivalents for content sitting directly on the off-black surface
 * (#16161a, i.e. TEXT_PRIMARY reused as a background), each contrast-
 * checked against WCAG AA (4.5:1 normal text) rather than eyeballed:
 *
 *   TEXT_PRIMARY_ON_DARK   #fafaf8 on #16161a -> 17.27:1
 *   TEXT_SECONDARY_ON_DARK #a8a5ac on #16161a -> 7.43:1
 *   TEXT_MUTED_ON_DARK     #8e8a92 on #16161a -> 5.33:1
 *   ACCENT_ON_DARK         #e65a42 on #16161a -> 5.07:1
 *
 * ACCENT_ON_DARK exists ONLY because the real, unmodified ACCENT
 * (#c4321e) measures 3.28:1 on #16161a -- passes the 3:1 non-text/UI-
 * component threshold (fine for a dot, border, or bar fill) but fails
 * AA for actual text. Anywhere the accent is rendered as TEXT on a dark
 * surface, use ACCENT_ON_DARK; anywhere it's a marker/fill/border, the
 * real ACCENT is fine and keeps the same hue everywhere else in the app.
 */
export const TEXT_PRIMARY_ON_DARK = '#fafaf8';
export const TEXT_SECONDARY_ON_DARK = '#a8a5ac';
export const TEXT_MUTED_ON_DARK = '#8e8a92';
export const ACCENT_ON_DARK = '#e65a42';
export const GRIDLINE_ON_DARK = '#2c2c32';

/** The on-dark equivalent of SIGNAL_LEVEL_COLOR (and, downstream,
 * RISK_TIER_COLOR/SEVERITY_COLOR/DRIFT_STATUS_COLOR -- no DECISION_COLOR
 * equivalent, same reason as the light-surface version above) --
 * needed everywhere a level color is used as a raw value (Recharts fills/
 * strokes, a badge's inline color, RiskMeter's fill) INSIDE a dark card,
 * since none of those are var()-based and so don't pick up card-dark's
 * CSS-cascade trick automatically. This isn't just a "nicer contrast"
 * upgrade -- the LIGHT-surface "noted" color (TEXT_PRIMARY, #16161a) is
 * literally the same value as the dark card background itself, so it
 * measures 1:1 (invisible) if used unmodified on a dark card, not just a
 * failing-AA number. Every raw-hex call site rendered on a dark surface
 * must use this map (or the tier/decision/severity maps resolved from it
 * below), never the light-surface one. */
export const SIGNAL_LEVEL_COLOR_ON_DARK: Record<SignalLevel, string> = {
  quiet: TEXT_SECONDARY_ON_DARK,
  noted: TEXT_PRIMARY_ON_DARK,
  alert: ACCENT_ON_DARK,
};

export const RISK_TIER_COLOR_ON_DARK: Record<'LOW' | 'MEDIUM' | 'HIGH', string> = {
  LOW: SIGNAL_LEVEL_COLOR_ON_DARK[RISK_TIER_LEVEL.LOW],
  MEDIUM: SIGNAL_LEVEL_COLOR_ON_DARK[RISK_TIER_LEVEL.MEDIUM],
  HIGH: SIGNAL_LEVEL_COLOR_ON_DARK[RISK_TIER_LEVEL.HIGH],
};

// No DECISION_COLOR_ON_DARK either, matching DECISION_COLOR's absence
// above -- same reason: nothing renders a decision as a raw color value,
// dark surface or not.

export const SEVERITY_COLOR_ON_DARK: Record<'NONE' | 'LOW' | 'MEDIUM' | 'HIGH', string> = {
  NONE: SIGNAL_LEVEL_COLOR_ON_DARK[SEVERITY_LEVEL.NONE],
  LOW: SIGNAL_LEVEL_COLOR_ON_DARK[SEVERITY_LEVEL.LOW],
  MEDIUM: SIGNAL_LEVEL_COLOR_ON_DARK[SEVERITY_LEVEL.MEDIUM],
  HIGH: SIGNAL_LEVEL_COLOR_ON_DARK[SEVERITY_LEVEL.HIGH],
};

// No SURFACE_INVERSE export here -- the dark surface color itself
// (nav rail + card-dark background) only ever needs to exist as a CSS
// custom property (--color-surface-inverse in index.css), never as a raw
// JS value; see that token's own docstring in index.css for why it's a
// standalone value rather than a var(--color-text-primary) reference.
