import { Line, LineChart, ResponsiveContainer, YAxis } from 'recharts';

export interface SparklinePoint {
  tick: number;
  value: number;
}

interface SparklineProps {
  points: SparklinePoint[];
  color: string;
  height?: number;
}

/** Minimal trend line -- no axes/gridlines, built for a small trend
 * strip rather than a full chart. Used by Fraud Spike for the live
 * fraud-rate trend built from already-fetched poll data (see that
 * page's own comment on why this is additive, not a backend change:
 * no new API calls, just retaining real values the page already
 * receives on each poll tick instead of discarding them).
 *
 * No glow (the monochrome/editorial direction has none anywhere) --
 * `color` sets a plain stroke. Current usage passes a neutral gray, not
 * the reserved accent: a sparkline is a visualization, not itself an
 * alert (see FraudSpike.tsx and the design plan's item 5).
 */
export function Sparkline({ points, color, height = 64 }: SparklineProps) {
  if (points.length < 2) {
    return (
      <div className="flex items-center text-xs text-text-muted" style={{ height }}>
        Collecting live readings...
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={points} margin={{ top: 4, right: 4, left: 4, bottom: 4 }}>
        <YAxis hide domain={['dataMin', 'dataMax']} />
        <Line
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
