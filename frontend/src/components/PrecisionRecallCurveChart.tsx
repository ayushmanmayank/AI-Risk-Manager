import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { TooltipContentProps } from 'recharts';
import {
  GRIDLINE,
  GRIDLINE_ON_DARK,
  TEXT_MUTED,
  TEXT_MUTED_ON_DARK,
  TEXT_PRIMARY,
  TEXT_PRIMARY_ON_DARK,
  TEXT_SECONDARY_ON_DARK,
  SERIES_COLOR,
} from '../theme/colors';

export interface CurvePoint {
  threshold: number;
  precision: number;
  recall: number;
}

interface PrecisionRecallCurveChartProps {
  points: CurvePoint[];
  currentThreshold: number;
  /** True on Threshold Simulator's now-dark chart card -- see
   * RiskTierBarChart's identical `onDark` prop for why Recharts props
   * need this explicitly (raw hex, not var()-based). */
  onDark?: boolean;
}

function formatPercent(value: string | number | boolean | null | undefined): string {
  return `${(Number(value ?? 0) * 100).toFixed(0)}%`;
}

function ChartTooltip({ active, payload, label }: TooltipContentProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-(--radius-control) border border-border bg-bg-surface px-3 py-2 text-sm">
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
 * tradeoff this whole page demonstrates. Two series -> a legend, per the
 * dataviz skill's rule that 2+ series always carry one. The current
 * slider position is marked with a vertical reference line so the
 * tradeoff at THIS threshold is visually obvious, not just readable from
 * the stat cards.
 *
 * ZERO accent on this chart, on purpose: this is model-performance data,
 * not risk-tier data, so the reserved signal color doesn't apply here at
 * all (see the design plan's item 5). Precision and recall are
 * differentiated by LINE STYLE instead -- solid (precision, the
 * "headline" metric this page is built around) vs. dashed (recall) --
 * plus a slightly heavier stroke weight on precision, the same
 * type-weight-over-color principle Badge.tsx uses for risk levels,
 * applied to a chart instead of a badge.
 */
export function PrecisionRecallCurveChart({ points, currentThreshold, onDark = false }: PrecisionRecallCurveChartProps) {
  const gridline = onDark ? GRIDLINE_ON_DARK : GRIDLINE;
  const mutedText = onDark ? TEXT_MUTED_ON_DARK : TEXT_MUTED;
  const primaryText = onDark ? TEXT_PRIMARY_ON_DARK : TEXT_PRIMARY;
  const precisionStroke = onDark ? TEXT_PRIMARY_ON_DARK : SERIES_COLOR.precision;
  const recallStroke = onDark ? TEXT_SECONDARY_ON_DARK : SERIES_COLOR.recall;

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={points} margin={{ top: 16, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={gridline} />
        <XAxis
          dataKey="threshold"
          type="number"
          domain={[0, 1]}
          ticks={[0, 0.2, 0.4, 0.6, 0.8, 1]}
          tickFormatter={formatPercent}
          tickLine={false}
          axisLine={{ stroke: gridline }}
          tick={{ fill: mutedText, fontSize: 12 }}
        />
        <YAxis
          domain={[0, 1]}
          tickFormatter={formatPercent}
          tickLine={false}
          axisLine={false}
          tick={{ fill: mutedText, fontSize: 12 }}
        />
        <Tooltip content={(props) => <ChartTooltip {...props} />} />
        <Legend
          verticalAlign="top"
          align="right"
          height={32}
          formatter={(value) => <span style={{ color: primaryText, fontSize: 13 }}>{value}</span>}
        />
        <ReferenceLine x={currentThreshold} stroke={primaryText} strokeDasharray="4 4" />
        <Line
          type="monotone"
          dataKey="precision"
          name="Precision"
          stroke={precisionStroke}
          strokeWidth={2.5}
          dot={false}
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="recall"
          name="Recall"
          stroke={recallStroke}
          strokeWidth={2}
          strokeDasharray="6 3"
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
