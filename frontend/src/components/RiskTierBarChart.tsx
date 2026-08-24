import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { TooltipContentProps } from 'recharts';
import {
  GRIDLINE,
  GRIDLINE_ON_DARK,
  RISK_TIER_COLOR,
  TEXT_MUTED,
  TEXT_MUTED_ON_DARK,
  TEXT_PRIMARY,
  TEXT_PRIMARY_ON_DARK,
} from '../theme/colors';
import type { RiskTier } from '../types/api';

interface RiskTierBarChartProps {
  counts: Record<RiskTier, number>;
  /** True when this chart renders on a card-dark surface (currently just
   * Dashboard, per the layout-revision preview) -- swaps axis/gridline/
   * label text to the on-dark tokens. Bar FILLS stay RISK_TIER_COLOR
   * unchanged either way: those are non-text/graphic use, already cleared
   * against the 3:1 threshold, and the accent hue shouldn't shift depending
   * on which card it's drawn on. */
  onDark?: boolean;
}

const TIER_ORDER: RiskTier[] = ['LOW', 'MEDIUM', 'HIGH'];

/** Fixed-surface tooltip -- deliberately NOT relying on the .card-dark
 * cascade trick here: that rule redefines --color-text-primary/secondary
 * but NOT --color-bg-surface/--color-border, and this tooltip sets its own
 * background independent of its ancestor card. Left to the cascade alone,
 * an on-dark card would flip the text to near-white while the background
 * stayed light beige -- invisible text. Both background and text are
 * chosen explicitly together instead, keyed off the same `onDark` flag the
 * chart itself uses. */
function ChartTooltip({ active, payload, onDark }: TooltipContentProps & { onDark: boolean }) {
  if (!active || !payload?.length) return null;
  const point = payload[0];
  const tier = (point.payload as { tier: RiskTier }).tier;
  return (
    <div
      className={`rounded-(--radius-control) border px-3 py-2 text-sm ${
        onDark
          ? 'border-border-on-dark bg-bg-surface-raised-on-dark'
          : 'border-border bg-bg-surface'
      }`}
    >
      <span className={onDark ? 'font-semibold text-text-primary-on-dark' : 'font-semibold text-text-primary'}>
        {tier}
      </span>
      <span className={onDark ? 'ml-2 font-mono text-text-secondary-on-dark' : 'ml-2 font-mono text-text-secondary'}>
        {Number(point.value).toLocaleString()} transactions
      </span>
    </div>
  );
}

/** Risk-tier distribution: magnitude across 3 categories -> bar chart.
 * Color follows the status palette (LOW=good, MEDIUM=warning, HIGH=critical);
 * the x-axis tick already labels each category in text, so color never
 * carries identity alone. Single series -> no legend box needed.
 */
export function RiskTierBarChart({ counts, onDark = false }: RiskTierBarChartProps) {
  const data = TIER_ORDER.map((tier) => ({ tier, count: counts[tier] ?? 0 }));
  const gridline = onDark ? GRIDLINE_ON_DARK : GRIDLINE;
  const axisText = onDark ? TEXT_PRIMARY_ON_DARK : TEXT_PRIMARY;
  const mutedText = onDark ? TEXT_MUTED_ON_DARK : TEXT_MUTED;

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 24, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={gridline} />
        <XAxis dataKey="tier" tickLine={false} axisLine={{ stroke: gridline }} tick={{ fill: axisText, fontSize: 13 }} />
        <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fill: mutedText, fontSize: 12 }} />
        <Tooltip content={(props) => <ChartTooltip {...props} onDark={onDark} />} cursor={{ fill: gridline, opacity: 0.4 }} />
        <Bar dataKey="count" barSize={40} radius={[4, 4, 0, 0]} isAnimationActive={false}>
          {data.map((entry) => (
            <Cell key={entry.tier} fill={RISK_TIER_COLOR[entry.tier]} />
          ))}
          <LabelList dataKey="count" position="top" fill={axisText} fontSize={13} fontWeight={600} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
