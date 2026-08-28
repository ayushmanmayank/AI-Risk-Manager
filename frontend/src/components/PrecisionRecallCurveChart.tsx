import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { TooltipContentProps } from 'recharts';
import { getPalette, getSeriesColor } from '../theme/colors';
import { useThemeMode } from '../theme/ThemeProvider';

export interface CurvePoint {
  threshold: number;
  precision: number;
  recall: number;
}

interface PrecisionRecallCurveChartProps {
  points: CurvePoint[];
  currentThreshold: number;
}

function formatPercent(value: string | number | boolean | null | undefined): string {
  return `${(Number(value ?? 0) * 100).toFixed(0)}%`;
}

function ChartTooltip({ active, payload, label }: TooltipContentProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border border-border bg-bg-surface-raised px-3 py-2 text-sm">
      <div className="font-mono font-semibold text-text-primary">threshold {Number(label).toFixed(2)}</div>
      {payload.map((entry) => (
        <div key={String(entry.dataKey)} className="font-mono" style={{ color: entry.color }}>
          {entry.name}: {formatPercent(entry.value as number)}
        </div>
      ))}
    </div>
  );
}

/** Precision & recall across the full 0-1 threshold range -- the core
 * tradeoff this page demonstrates. Same color system as the rest of the
 * app: precision (the page's headline metric) gets the reserved accent;
 * recall stays neutral, differentiated further by dashed line style. The
 * current slider position is marked with a vertical reference line
 * (`.pr-threshold-line` in index.css transitions its x1/x2 smoothly on
 * every debounced threshold change instead of snapping -- SVG geometry
 * properties are CSS-transitionable the same way color/opacity are).
 */
export function PrecisionRecallCurveChart({ points, currentThreshold }: PrecisionRecallCurveChartProps) {
  const mode = useThemeMode();
  const palette = getPalette(mode);
  const series = getSeriesColor(mode);

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={points} margin={{ top: 16, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={palette.gridline} />
        <XAxis
          dataKey="threshold"
          type="number"
          domain={[0, 1]}
          ticks={[0, 0.2, 0.4, 0.6, 0.8, 1]}
          tickFormatter={formatPercent}
          tickLine={false}
          axisLine={{ stroke: palette.gridline }}
          tick={{ fill: palette.textMuted, fontSize: 12 }}
        />
        <YAxis domain={[0, 1]} tickFormatter={formatPercent} tickLine={false} axisLine={false} tick={{ fill: palette.textMuted, fontSize: 12 }} />
        <Tooltip content={(props) => <ChartTooltip {...props} />} />
        <Legend
          verticalAlign="top"
          align="right"
          height={32}
          formatter={(value) => <span style={{ color: palette.textPrimary, fontSize: 13 }}>{value}</span>}
        />
        <ReferenceLine x={currentThreshold} stroke={palette.accent} strokeDasharray="4 4" className="pr-threshold-line" />
        <Line
          type="monotone"
          dataKey="precision"
          name="Precision"
          stroke={series.precision}
          strokeWidth={2.5}
          dot={false}
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="recall"
          name="Recall"
          stroke={series.recall}
          strokeWidth={2}
          strokeDasharray="6 3"
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
