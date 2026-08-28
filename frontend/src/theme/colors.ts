/**
 * DARK-GOLD ANIMATED THEME (feature/frontend-final-v3) -- full replacement
 * of the monochrome/editorial system. Unlike every prior direction in this
 * app's history, this one is a genuine two-mode system: the whole page
 * switches between a dark and a light palette via the `data-theme`
 * attribute on <html> (see ThemeProvider.tsx), not a per-card `onDark`
 * prop. Every Tailwind color utility (`text-text-primary`, `bg-bg-surface`,
 * `border-border`, etc.) resolves through CSS custom properties defined in
 * index.css's `:root`/`[data-theme="light"]` blocks, so those follow the
 * active mode automatically with zero JS involvement.
 *
 * This file exists for the values that DON'T get that for free: Recharts
 * fills/strokes, SVG stroke props, and inline `style` colors (badge dots,
 * RiskMeter fill) are raw hex, not var()-based -- CSS custom properties
 * only resolve inside an actual CSS context (a stylesheet or a `style`
 * attribute), not a bare SVG presentation attribute string, so passing
 * `fill="var(--color-accent)"` directly to a Recharts <Bar> is not
 * reliable. Every helper below takes an explicit `mode: ThemeMode`
 * instead, mirroring the exact shape of the old `onDark: boolean` prop
 * this replaces -- call sites read `useThemeMode()` once and pass `mode`
 * down, same wiring pattern as before, different source of truth.
 *
 * THE THREE-COLOR SYSTEM: LOW risk gets the reserved gold (`accent`)
 * itself -- a real philosophical reversal from the prior monochrome
 * system, where LOW/MEDIUM were deliberately uncolored and only HIGH
 * earned the accent. Here accent means "the brand color," used for LOW
 * tier, the active nav underline, and primary buttons; MEDIUM gets a
 * distinct amber; HIGH/critical alerts get a rose -- see getLevelColor.
 *
 * LIGHT-MODE CONTRAST: every pair below is COMPUTED (WCAG 2.x sRGB
 * relative-luminance formula), not eyeballed -- see the ratios inline.
 * Two of the light-mode hex values were explicitly revised DARKER than
 * the literal spec draft because the computed ratio failed AA text
 * contrast (4.5:1) against the white card surface -- the spec itself
 * called this out for accent-amber ("darken if it fails WCAG AA"); the
 * same discipline was extended to accent-rose, which measured 4.32:1
 * (short of 4.5:1) at the originally-given value:
 *
 *   textSecondary  #8A7A4A -> revised #75663A  (4.23:1 -> 5.65:1 on white)
 *   accentAmber    #C99A3E -> revised #8C6A1E  (2.57:1 -> 5.01:1 on white)
 *   accentRose     #C9506E -> revised #C04665  (4.32:1 -> 4.88:1 on white)
 *
 * `accent` itself is UNCHANGED from the spec (#B8860B, 3.25:1 on white) --
 * it clears the 3:1 non-text/UI-component threshold but not 4.5:1 text,
 * which is exactly why the spec restricts it to "large UI elements/icons,
 * never small body text." That restriction is enforced structurally here:
 * getLevelColor's light-mode 'low' case returns textPrimary for TEXT use
 * (badge labels), not the raw accent -- accent itself still paints LOW's
 * dot/border/fill, which are graphical, not text, and only need 3:1.
 */

import type { AlertSeverity, Decision, DriftStatus, RiskTier } from '../types/api';

export type ThemeMode = 'light' | 'dark';

export interface Palette {
  textPrimary: string;
  textSecondary: string;
  /** A third, dimmer text tier for supplementary captions/ids/timestamps
   * -- checked against the 3:1 non-text/large-text threshold rather than
   * 4.5:1 (same tier the prior system's TEXT_MUTED occupied). */
  textMuted: string;
  border: string;
  surface: string;
  /** A step lighter/more distinct than `surface` -- dropdown panels,
   * skeleton placeholders, table-row hover tint, progress-bar tracks. */
  surfaceRaised: string;
  accent: string;
  accentAmber: string;
  accentRose: string;
  gridline: string;
  /** Neutral, non-status color for "the norm"/baseline series (e.g. Fraud
   * Spike's baseline-vs-current bars) -- deliberately gray, not a level
   * color, so the "current" bar (colored by severity) reads as the one
   * thing actually varying. Graphic use only (a bar fill) -- checked
   * against the 3:1 non-text threshold, not 4.5:1. */
  baseline: string;
}

// DARK -- default mode. Every ratio below is against the --bg-surface
// value (rgba(19,20,23,0.8)) composited over the animated canvas gradient
// at its darkest and lightest stops -- the range stays 16.4-16.9:1 for
// text-primary, 5.6-5.8:1 for text-secondary/accent, 7.1-7.3:1 for
// accent-amber, 5.3-5.5:1 for accent-rose across every stop, so one
// representative figure per token is accurate everywhere the gradient
// animates through.
export const DARK_PALETTE: Palette = {
  textPrimary: '#F2F4F0', // 16.6:1 on composited surface
  textSecondary: '#8B8F94', // 5.7:1
  textMuted: '#6B6E73', // 3.6:1 -- captions/ids/timestamps tier
  border: '#2A2410',
  surface: 'rgba(19, 20, 23, 0.8)',
  surfaceRaised: 'rgba(30, 31, 35, 0.9)',
  accent: '#B8860B', // 5.7:1 -- safe as text here, unlike light mode
  accentAmber: '#C99A3E', // 7.2:1
  accentRose: '#E0607A', // 5.4:1
  gridline: '#2A2410',
  baseline: '#75797E', // 4.2:1, graphic-use bar fill
};

// LIGHT -- toggled. See the file docstring for the two revised hex values
// and their computed ratios (all against #FFFFFF, the card surface text
// actually sits on -- not the canvas gradient behind cards).
export const LIGHT_PALETTE: Palette = {
  textPrimary: '#3A2E00', // 13.4:1 on white
  textSecondary: '#75663A', // 5.65:1 (revised from spec's #8A7A4A, 4.23:1)
  textMuted: '#8F8362', // 3.76:1 -- captions/ids/timestamps tier
  border: '#E8DFC0',
  surface: '#FFFFFF',
  surfaceRaised: '#F7F3E8',
  accent: '#B8860B', // 3.25:1 -- large UI/icons/decorative only, see below
  accentAmber: '#8C6A1E', // 5.01:1 (revised from spec's #C99A3E, 2.57:1)
  accentRose: '#C04665', // 4.88:1 (revised from spec's #C9506E, 4.32:1)
  gridline: '#E8DFC0',
  baseline: '#93876B', // 3.55:1, graphic-use bar fill
};

export function getPalette(mode: ThemeMode): Palette {
  return mode === 'dark' ? DARK_PALETTE : LIGHT_PALETTE;
}

/** The 3-level system every status reading in the app resolves through:
 * risk tier, decision, alert severity, and drift status are all, at
 * bottom, "how concerned should you be" on the same low/medium/high
 * scale -- see RISK_TIER_LEVEL/DECISION_LEVEL/SEVERITY_LEVEL/
 * DRIFT_STATUS_LEVEL below, each mapping their own domain vocabulary onto
 * this one shared scale so there is exactly one place a color is chosen
 * for "medium," not four. */
export type SignalLevel = 'low' | 'medium' | 'high';

/** Fill/dot/border color for a level -- always safe to use as a graphical
 * (non-text) value: dots, borders, chart fills, ring strokes. For BADGE
 * TEXT specifically, use getLevelTextColor instead, which enforces the
 * light-mode "accent is never small body text" rule. */
export function getLevelColor(mode: ThemeMode, level: SignalLevel): string {
  const p = getPalette(mode);
  if (level === 'low') return p.accent;
  if (level === 'medium') return p.accentAmber;
  return p.accentRose;
}

/** Text-safe color for a level. In dark mode every level color already
 * clears 4.5:1 (5.6-7.2:1), so text can use the same value as the fill.
 * In light mode, raw `accent` only clears 3.25:1 (fails AA text) -- LOW's
 * text falls back to textPrimary instead, matching the spec's explicit
 * "accent reserved for large UI elements/icons, never small body text"
 * rule; MEDIUM/HIGH's revised amber/rose both clear 4.5:1 so they keep
 * their own color as text. */
export function getLevelTextColor(mode: ThemeMode, level: SignalLevel): string {
  const p = getPalette(mode);
  if (mode === 'light' && level === 'low') return p.textPrimary;
  return getLevelColor(mode, level);
}

export const RISK_TIER_LEVEL: Record<RiskTier, SignalLevel> = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
};

/** Decisions map 1:1 onto the same severity as their risk tier
 * (ALLOW<-LOW, REVIEW<-MEDIUM, HOLD<-HIGH). */
export const DECISION_LEVEL: Record<Decision, SignalLevel> = {
  ALLOW: 'low',
  REVIEW: 'medium',
  HOLD: 'high',
};

/** NONE and LOW both fold into 'low' -- their own label text already
 * carries the distinction; a z-score that's mild-but-nonzero doesn't
 * warrant the same visual weight as a genuinely elevated MEDIUM/HIGH
 * reading. See src/anomaly/spike_detector.py for where these come from. */
export const SEVERITY_LEVEL: Record<AlertSeverity, SignalLevel> = {
  NONE: 'low',
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
};

export const DRIFT_STATUS_LEVEL: Record<DriftStatus, SignalLevel> = {
  STABLE: 'low',
  MODERATE_DRIFT: 'medium',
  SIGNIFICANT_DRIFT: 'high',
};

export function getRiskTierColor(mode: ThemeMode): Record<RiskTier, string> {
  return {
    LOW: getLevelColor(mode, RISK_TIER_LEVEL.LOW),
    MEDIUM: getLevelColor(mode, RISK_TIER_LEVEL.MEDIUM),
    HIGH: getLevelColor(mode, RISK_TIER_LEVEL.HIGH),
  };
}

export function getSeverityColor(mode: ThemeMode): Record<AlertSeverity, string> {
  return {
    NONE: getLevelColor(mode, SEVERITY_LEVEL.NONE),
    LOW: getLevelColor(mode, SEVERITY_LEVEL.LOW),
    MEDIUM: getLevelColor(mode, SEVERITY_LEVEL.MEDIUM),
    HIGH: getLevelColor(mode, SEVERITY_LEVEL.HIGH),
  };
}

export function getDriftStatusColor(mode: ThemeMode): Record<DriftStatus, string> {
  return {
    STABLE: getLevelColor(mode, DRIFT_STATUS_LEVEL.STABLE),
    MODERATE_DRIFT: getLevelColor(mode, DRIFT_STATUS_LEVEL.MODERATE_DRIFT),
    SIGNIFICANT_DRIFT: getLevelColor(mode, DRIFT_STATUS_LEVEL.SIGNIFICANT_DRIFT),
  };
}

/** Precision/recall (Threshold Simulator): precision (the page's
 * "headline" metric) gets the reserved accent; recall stays neutral
 * (textSecondary) -- differentiated further by line style (solid vs.
 * dashed) in PrecisionRecallCurveChart.tsx. Per the Phase 3 spec ("same
 * color system" as Fraud Spike's accent-stroked trend line), this
 * deliberately reintroduces the accent here, reversing the prior
 * monochrome system's "zero accent on this chart" rule. */
export function getSeriesColor(mode: ThemeMode): { precision: string; recall: string } {
  const p = getPalette(mode);
  return { precision: p.accent, recall: p.textSecondary };
}
