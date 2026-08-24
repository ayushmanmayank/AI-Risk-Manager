import { getAnalytics } from '../api/client';
import { useApiData } from '../api/hooks';
import { EmptyBlock, ErrorBlock } from '../components/AsyncState';
import { RadialRing } from '../components/RadialRing';
import { RiskTierBarChart } from '../components/RiskTierBarChart';
import { StatCard } from '../components/StatCard';
import { Skeleton } from '../components/ui/skeleton';
import { useCountUp, useSweepInOnMount } from '../hooks/useCountUp';
import { RISK_TIER_COLOR } from '../theme/colors';
// PREVIEW ONLY: Dashboard is the one page opted into the card-dark layout
// revision for this round of review -- see StatCard/RiskTierBarChart's
// `onDark` props and index.css's `card-dark` utility docstring. The other
// 8 pages are untouched until this is approved.
import type { AnalyticsOut, Decision, RiskTier } from '../types/api';
import { formatAmount, formatPercent } from '../utils/format';

const RISK_TIERS: RiskTier[] = ['LOW', 'MEDIUM', 'HIGH'];
const DECISIONS: Decision[] = ['ALLOW', 'REVIEW', 'HOLD'];

export function Dashboard() {
  const analytics = useApiData<AnalyticsOut>(getAnalytics);

  if (analytics.status === 'loading') {
    return <DashboardSkeleton />;
  }

  if (analytics.status === 'error') {
    return <ErrorBlock message={analytics.error.message} onRetry={analytics.refetch} />;
  }

  const data = analytics.data;

  if (data.total_transactions === 0) {
    return (
      <EmptyBlock
        title="No predictions yet"
        description="Once transactions are scored via POST /api/v1/predict, this dashboard will populate with live risk metrics."
      />
    );
  }

  const tierCounts = Object.fromEntries(
    RISK_TIERS.map((tier) => [tier, data.count_by_risk_tier[tier] ?? 0]),
  ) as Record<RiskTier, number>;

  const decisionCounts = Object.fromEntries(
    DECISIONS.map((decision) => [decision, data.count_by_decision[decision] ?? 0]),
  ) as Record<Decision, number>;

  return <DashboardBody data={data} tierCounts={tierCounts} decisionCounts={decisionCounts} />;
}

/** Split out from Dashboard() so the signature-element hooks below
 * (useCountUp/useSweepInOnMount) only ever mount once real data exists --
 * calling them unconditionally in Dashboard() itself would violate the
 * rules of hooks against its early loading/error/empty returns above. */
function DashboardBody({
  data,
  tierCounts,
  decisionCounts,
}: {
  data: AnalyticsOut;
  tierCounts: Record<RiskTier, number>;
  decisionCounts: Record<Decision, number>;
}) {
  // Design plan's signature element: the HIGH-tier ring sweeps and its
  // two numbers (the ring's own percent label, and the count beside it)
  // count up together, in sync, driven by the same real fetched value --
  // never a placeholder, only an animated path to the real number.
  const highTierPercent = data.total_transactions > 0 ? (tierCounts.HIGH / data.total_transactions) * 100 : 0;
  const animatedRingPercent = useSweepInOnMount(highTierPercent);
  const animatedRingLabelPercent = useCountUp(highTierPercent);
  const animatedHighCount = useCountUp(tierCounts.HIGH);

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard onDark label="Total transactions scored" value={data.total_transactions.toLocaleString()} />
        <StatCard onDark label="Average expected loss" value={formatAmount(data.average_expected_loss)} />
        {/* Genuine value-of-whole metric (HIGH count / total) -> radial
            ring, per the design plan. The OTHER HIGH-tier stat below
            ("fraud rate among HIGH tier") stays a plain card -- it's
            frequently N/A (no ground truth to compute it from yet), which
            is a poor fit for a ring. */}
        <div className="card-dark flex items-center gap-4 p-4">
          <RadialRing
            percent={animatedRingPercent}
            color={RISK_TIER_COLOR.HIGH}
            size={72}
            strokeWidth={7}
            label={
              /* text-risk-high (=ACCENT, #c4321e) only clears 3.28:1 on
                 this dark card -- fails AA text (4.5:1). ACCENT_ON_DARK
                 (#e65a42, 5.07:1) is the on-dark equivalent; the ring's
                 ARC stays plain ACCENT via RISK_TIER_COLOR.HIGH above,
                 since a stroke is non-text and 3.28:1 already clears the
                 3:1 UI-component threshold. */
              <span className="font-mono text-sm font-semibold tabular-nums text-accent-on-dark">
                {animatedRingLabelPercent.toFixed(1)}%
              </span>
            }
          />
          <div>
            <div className="text-sm text-text-secondary">HIGH-tier count</div>
            <div className="font-mono text-lg font-semibold tabular-nums text-text-primary">
              {Math.round(animatedHighCount).toLocaleString()}
            </div>
          </div>
        </div>
        <StatCard
          onDark
          label="Fraud rate among HIGH tier"
          value={data.high_tier_fraud_rate === null ? 'N/A' : `${(data.high_tier_fraud_rate * 100).toFixed(1)}%`}
          caption={data.high_tier_fraud_rate === null ? data.high_tier_fraud_rate_note : undefined}
        />
      </div>

      <div className="card-dark p-6">
        <h2 className="font-display text-base font-semibold text-text-primary">Risk tier distribution</h2>
        <RiskTierBarChart counts={tierCounts} onDark />
        <div className="mt-2 flex gap-6 text-sm text-text-secondary">
          {RISK_TIERS.map((tier) => (
            <span key={tier} className="flex items-center gap-2">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: RISK_TIER_COLOR[tier] }}
              />
              {tier}: {tierCounts[tier].toLocaleString()} ({formatPercent(tierCounts[tier], data.total_transactions)})
            </span>
          ))}
        </div>
      </div>

      <div className="card-dark p-6">
        <h2 className="font-display text-base font-semibold text-text-primary">Decisions</h2>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
          {DECISIONS.map((decision) => (
            <StatCard
              onDark
              key={decision}
              label={decision}
              value={decisionCounts[decision].toLocaleString()}
              caption={formatPercent(decisionCounts[decision], data.total_transactions)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
      <Skeleton className="h-72" />
    </div>
  );
}
