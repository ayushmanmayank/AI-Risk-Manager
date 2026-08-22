import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { TooltipContentProps } from 'recharts';
import { GRIDLINE, RISK_TIER_COLOR, TEXT_MUTED, TEXT_PRIMARY } from '../theme/colors';
import type { RiskTier } from '../types/api';

interface RiskTierBarChartProps {
  counts: Record<RiskTier, number>;
}

const TIER_ORDER: RiskTier[] = ['LOW', 'MEDIUM', 'HIGH'];

function ChartTooltip({ active, payload }: TooltipContentProps) {
  if (!active || !payload?.length) return null;
  const point = payload[0];
  const tier = (point.payload as { tier: RiskTier }).tier;
  return (
    <div className="rounded-md border border-[#e1e0d9] bg-[#fcfcfb] px-3 py-2 text-sm shadow-sm">
      <span className="font-semibold text-[#0b0b0b]">{tier}</span>
      <span className="ml-2 text-[#52514e]">{Number(point.value).toLocaleString()} transactions</span>
    </div>
  );
}

/** Risk-tier distribution: magnitude across 3 categories -> bar chart.
 * Color follows the status palette (LOW=good, MEDIUM=warning, HIGH=critical);
 * the x-axis tick already labels each category in text, so color never
 * carries identity alone. Single series -> no legend box needed.
 */
export function RiskTierBarChart({ counts }: RiskTierBarChartProps) {
  const data = TIER_ORDER.map((tier) => ({ tier, count: counts[tier] ?? 0 }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 24, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={GRIDLINE} />
        <XAxis
          dataKey="tier"
          tickLine={false}
          axisLine={{ stroke: GRIDLINE }}
          tick={{ fill: TEXT_PRIMARY, fontSize: 13 }}
        />
        <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fill: TEXT_MUTED, fontSize: 12 }} />
        <Tooltip content={(props) => <ChartTooltip {...props} />} cursor={{ fill: GRIDLINE, opacity: 0.4 }} />
        <Bar dataKey="count" barSize={40} radius={[4, 4, 0, 0]}>
          {data.map((entry) => (
            <Cell key={entry.tier} fill={RISK_TIER_COLOR[entry.tier]} />
          ))}
          <LabelList dataKey="count" position="top" fill={TEXT_PRIMARY} fontSize={13} fontWeight={600} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
