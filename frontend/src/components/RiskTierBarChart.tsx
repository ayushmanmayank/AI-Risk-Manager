import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { TooltipContentProps } from 'recharts';
import { getPalette, getRiskTierColor } from '../theme/colors';
import { useThemeMode } from '../theme/ThemeProvider';
import type { RiskTier } from '../types/api';

const TIER_ORDER: RiskTier[] = ['LOW', 'MEDIUM', 'HIGH'];

/** Themed via ordinary Tailwind utility classes -- this is a plain HTML
 * div, so it picks up the active mode through the same CSS custom
 * properties every card does, no raw hex/mode prop needed here. */
function ChartTooltip({ active, payload }: TooltipContentProps) {
  if (!active || !payload?.length) return null;
  const point = payload[0];
  const tier = (point.payload as { tier: RiskTier }).tier;
  return (
    <div className="rounded-md border border-border bg-bg-surface-raised px-3 py-2 text-sm">
      <span className="font-semibold text-text-primary">{tier}</span>
      <span className="ml-2 font-mono text-text-secondary">{Number(point.value).toLocaleString()} transactions</span>
    </div>
  );
}

/** Risk-tier distribution: magnitude across 3 categories -> bar chart.
 * Fill color follows the shared low/medium/high signal scale (LOW=gold,
 * MEDIUM=amber, HIGH=rose); the x-axis tick already labels each category
 * in text, so color never carries identity alone. Bars animate their
 * height in on data load (matches the Model Performance bar spec).
 */
export function RiskTierBarChart({ counts }: { counts: Record<RiskTier, number> }) {
  const mode = useThemeMode();
  const palette = getPalette(mode);
  const tierColor = getRiskTierColor(mode);
  const data = TIER_ORDER.map((tier) => ({ tier, count: counts[tier] ?? 0 }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 24, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={palette.gridline} />
        <XAxis
          dataKey="tier"
          tickLine={false}
          axisLine={{ stroke: palette.gridline }}
          tick={{ fill: palette.textPrimary, fontSize: 13 }}
        />
        <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fill: palette.textMuted, fontSize: 12 }} />
        <Tooltip content={(props) => <ChartTooltip {...props} />} cursor={{ fill: palette.gridline, opacity: 0.4 }} />
        <Bar dataKey="count" barSize={40} radius={[4, 4, 0, 0]} isAnimationActive animationDuration={300} animationEasing="ease-out">
          {data.map((entry) => (
            <Cell key={entry.tier} fill={tierColor[entry.tier]} />
          ))}
          <LabelList dataKey="count" position="top" fill={palette.textPrimary} fontSize={13} fontWeight={600} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
