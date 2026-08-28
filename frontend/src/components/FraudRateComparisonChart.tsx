import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { TooltipContentProps } from 'recharts';
import { SEVERITY_LEVEL, getLevelColor, getPalette } from '../theme/colors';
import { useThemeMode } from '../theme/ThemeProvider';
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
    <div className="rounded-md border border-border bg-bg-surface-raised px-3 py-2 text-sm">
      <span className="font-semibold text-text-primary">{label}</span>
      <span className="ml-2 font-mono text-text-secondary">{formatRatePercent(Number(point.value))} HIGH-risk</span>
    </div>
  );
}

/** Two-bar comparison: baseline (neutral) vs current (colored by
 * severity) fraud rate. The "Current" bar's color is the one dynamic
 * element, directly encoding how alarming the live rate is at a glance.
 * Bars animate in on data load, matching the Model Performance spec. */
export function FraudRateComparisonChart({ currentRate, baselineRate, severity }: FraudRateComparisonChartProps) {
  const mode = useThemeMode();
  const palette = getPalette(mode);
  const currentFill = getLevelColor(mode, SEVERITY_LEVEL[severity]);
  const data = [
    { key: 'baseline', label: 'Baseline', rate: baselineRate },
    { key: 'current', label: 'Current', rate: currentRate },
  ];

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 24, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={palette.gridline} />
        <XAxis
          dataKey="label"
          tickLine={false}
          axisLine={{ stroke: palette.gridline }}
          tick={{ fill: palette.textPrimary, fontSize: 13 }}
        />
        <YAxis tickFormatter={formatRatePercent} tickLine={false} axisLine={false} tick={{ fill: palette.textMuted, fontSize: 12 }} />
        <Tooltip content={(props) => <ChartTooltip {...props} />} cursor={{ fill: palette.gridline, opacity: 0.4 }} />
        <Bar dataKey="rate" barSize={64} radius={[4, 4, 0, 0]} minPointSize={2} isAnimationActive animationDuration={300} animationEasing="ease-out">
          <Cell fill={palette.baseline} />
          <Cell fill={currentFill} />
          <LabelList dataKey="rate" position="top" formatter={formatRatePercent} fill={palette.textPrimary} fontSize={13} fontWeight={600} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
