import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { TooltipContentProps } from 'recharts';
import { GRIDLINE, SERIES_COLOR, TEXT_MUTED, TEXT_PRIMARY } from '../theme/colors';

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
    <div className="rounded-md border border-border bg-bg-surface px-3 py-2 text-sm">
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
 * tradeoff this whole page demonstrates. Two series -> fixed categorical
 * colors (never status colors) plus a legend, per the dataviz skill's
 * rule that 2+ series always carry a legend. The current slider position
 * is marked with a vertical reference line so the tradeoff at THIS
 * threshold is visually obvious, not just readable from the stat cards.
 *
 * Deliberate deviation from the redesign's "single accent color per
 * chart" default: this chart's entire job is comparing two series, so
 * collapsing to one color would destroy the thing the page exists to
 * show. Precision (violet, glowing -- the "headline" metric this page
 * is built around) is the only violet element on this chart; Recall
 * gets a plain, unglowed neutral so violet keeps exactly one meaning.
 */
export function PrecisionRecallCurveChart({ points, currentThreshold }: PrecisionRecallCurveChartProps) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={points} margin={{ top: 16, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={GRIDLINE} />
        <XAxis
          dataKey="threshold"
          type="number"
          domain={[0, 1]}
          ticks={[0, 0.2, 0.4, 0.6, 0.8, 1]}
          tickFormatter={formatPercent}
          tickLine={false}
          axisLine={{ stroke: GRIDLINE }}
          tick={{ fill: TEXT_MUTED, fontSize: 12 }}
        />
        <YAxis
          domain={[0, 1]}
          tickFormatter={formatPercent}
          tickLine={false}
          axisLine={false}
          tick={{ fill: TEXT_MUTED, fontSize: 12 }}
        />
        <Tooltip content={(props) => <ChartTooltip {...props} />} />
        <Legend
          verticalAlign="top"
          align="right"
          height={32}
          formatter={(value) => <span style={{ color: TEXT_PRIMARY, fontSize: 13 }}>{value}</span>}
        />
        <ReferenceLine x={currentThreshold} stroke={TEXT_PRIMARY} strokeDasharray="4 4" />
        <Line
          type="monotone"
          dataKey="precision"
          name="Precision"
          stroke={SERIES_COLOR.precision}
          strokeWidth={2.5}
          dot={false}
          isAnimationActive={false}
          className="glow-line"
        />
        <Line
          type="monotone"
          dataKey="recall"
          name="Recall"
          stroke={SERIES_COLOR.recall}
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
