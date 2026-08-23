import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { TooltipContentProps } from 'recharts';
import { BASELINE_COLOR, GRIDLINE, SEVERITY_COLOR, TEXT_MUTED, TEXT_PRIMARY } from '../theme/colors';
import type { AlertSeverity } from '../types/api';

interface FraudRateComparisonChartProps {
  currentRate: number;
  baselineRate: number;
  severity: AlertSeverity;
}

function formatRatePercent(value: string | number | boolean | null | undefined): string {
  return `${(Number(value ?? 0) * 100).toFixed(2)}%`;
}

function ChartTooltip({ active, payload }: TooltipContentProps) {
  if (!active || !payload?.length) return null;
  const point = payload[0];
  const label = (point.payload as { label: string }).label;
  return (
    <div className="rounded-md border border-border bg-bg-surface px-3 py-2 text-sm">
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
export function FraudRateComparisonChart({ currentRate, baselineRate, severity }: FraudRateComparisonChartProps) {
  const data = [
    { key: 'baseline', label: 'Baseline', rate: baselineRate },
    { key: 'current', label: 'Current', rate: currentRate },
  ];

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 24, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={GRIDLINE} />
        <XAxis dataKey="label" tickLine={false} axisLine={{ stroke: GRIDLINE }} tick={{ fill: TEXT_PRIMARY, fontSize: 13 }} />
        <YAxis
          tickFormatter={formatRatePercent}
          tickLine={false}
          axisLine={false}
          tick={{ fill: TEXT_MUTED, fontSize: 12 }}
        />
        <Tooltip content={(props) => <ChartTooltip {...props} />} cursor={{ fill: GRIDLINE, opacity: 0.4 }} />
        <Bar dataKey="rate" barSize={64} radius={[4, 4, 0, 0]} minPointSize={2} isAnimationActive={false}>
          <Cell fill={BASELINE_COLOR} />
          <Cell fill={SEVERITY_COLOR[severity]} />
          <LabelList dataKey="rate" position="top" formatter={formatRatePercent} fill={TEXT_PRIMARY} fontSize={13} fontWeight={600} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
