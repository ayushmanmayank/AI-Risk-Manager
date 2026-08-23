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

/** Minimal glowing line -- no axes/gridlines, built for a small trend
 * strip rather than a full chart. Used by Fraud Spike for the live
 * fraud-rate trend built from already-fetched poll data (see that
 * page's own comment on why this is additive, not a backend change:
 * no new API calls, just retaining real values the page already
 * receives on each poll tick instead of discarding them).
 *
 * The glow itself is the shared .glow-line CSS class (fixed violet),
 * independent of the `color` prop below -- `color` only sets the stroke.
 * Every current usage passes the violet ACCENT for both anyway (this
 * component is reserved for "live" trend strips, an inherently
 * UI-signal context per the design plan), so this hasn't been an issue,
 * but a future caller passing a different stroke color would get a
 * violet glow around it -- worth revisiting if that ever comes up.
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
        {/* Glow via the shared .glow-line CSS class, not Recharts' `style`
            prop -- see index.css's comment: a `style` object passed
            directly to <Line> was found to silently break its rendering. */}
        <Line
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
          className="glow-line"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
