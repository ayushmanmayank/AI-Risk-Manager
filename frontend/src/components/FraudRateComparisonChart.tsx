import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { TooltipContentProps } from 'recharts';
import {
  BASELINE_COLOR,
  GRIDLINE,
  GRIDLINE_ON_DARK,
  SEVERITY_COLOR,
  SEVERITY_COLOR_ON_DARK,
  TEXT_MUTED,
  TEXT_MUTED_ON_DARK,
  TEXT_PRIMARY,
  TEXT_PRIMARY_ON_DARK,
} from '../theme/colors';
import type { AlertSeverity } from '../types/api';

interface FraudRateComparisonChartProps {
  currentRate: number;
  baselineRate: number;
  severity: AlertSeverity;
  /** True on Fraud Spike's now-dark chart card. BASELINE_COLOR is left
   * unswapped -- it already clears AA (8.44:1) against the dark card
   * background as-is. SEVERITY_COLOR's "noted"/MEDIUM value does not
   * (see theme/colors.ts): it's the same color as the card background
   * itself, so the "Current" bar would be invisible at that severity
   * without this. */
  onDark?: boolean;
}

function formatRatePercent(value: string | number | boolean | null | undefined): string {
  return `${(Number(value ?? 0) * 100).toFixed(2)}%`;
}

function ChartTooltip({ active, payload }: TooltipContentProps) {
  if (!active || !payload?.length) return null;
  const point = payload[0];
  const label = (point.payload as { label: string }).label;
  return (
    <div className="rounded-(--radius-control) border border-border bg-bg-surface px-3 py-2 text-sm">
      <span className="font-semibold text-text-primary">{label}</span>
      <span className="ml-2 font-mono text-text-secondary">{formatRatePercent(Number(point.value))} HIGH-risk</span>
    </div>
  );
}

/** Two-bar comparison: baseline (neutral) vs current (colored by severity)
 * fraud rate. Same bar-chart form as RiskTierBarChart for visual
 * consistency; the "Current" bar's color is the one dynamic element,
 * directly encoding how alarming the live rate is at a glance.
 */
export function FraudRateComparisonChart({ currentRate, baselineRate, severity, onDark = false }: FraudRateComparisonChartProps) {
  const data = [
    { key: 'baseline', label: 'Baseline', rate: baselineRate },
    { key: 'current', label: 'Current', rate: currentRate },
  ];
  const gridline = onDark ? GRIDLINE_ON_DARK : GRIDLINE;
  const axisText = onDark ? TEXT_PRIMARY_ON_DARK : TEXT_PRIMARY;
  const mutedText = onDark ? TEXT_MUTED_ON_DARK : TEXT_MUTED;
  const currentFill = onDark ? SEVERITY_COLOR_ON_DARK[severity] : SEVERITY_COLOR[severity];

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 24, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={gridline} />
        <XAxis dataKey="label" tickLine={false} axisLine={{ stroke: gridline }} tick={{ fill: axisText, fontSize: 13 }} />
        <YAxis
          tickFormatter={formatRatePercent}
          tickLine={false}
          axisLine={false}
          tick={{ fill: mutedText, fontSize: 12 }}
        />
        <Tooltip content={(props) => <ChartTooltip {...props} />} cursor={{ fill: gridline, opacity: 0.4 }} />
        <Bar dataKey="rate" barSize={64} radius={[4, 4, 0, 0]} minPointSize={2} isAnimationActive={false}>
          <Cell fill={BASELINE_COLOR} />
          <Cell fill={currentFill} />
          <LabelList dataKey="rate" position="top" formatter={formatRatePercent} fill={axisText} fontSize={13} fontWeight={600} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
