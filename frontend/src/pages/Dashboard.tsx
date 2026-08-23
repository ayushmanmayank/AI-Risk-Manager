import { getAnalytics } from '../api/client';
import { useApiData } from '../api/hooks';
import { EmptyBlock, ErrorBlock } from '../components/AsyncState';
import { RadialRing } from '../components/RadialRing';
import { RiskTierBarChart } from '../components/RiskTierBarChart';
import { StatCard } from '../components/StatCard';
import { RISK_TIER_COLOR } from '../theme/colors';
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

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total transactions scored" value={data.total_transactions.toLocaleString()} />
        <StatCard label="Average expected loss" value={formatAmount(data.average_expected_loss)} />
        {/* Genuine value-of-whole metric (HIGH count / total) -> radial
            ring, per the design plan. The OTHER HIGH-tier stat below
            ("fraud rate among HIGH tier") stays a plain card -- it's
            frequently N/A (no ground truth to compute it from yet), which
            is a poor fit for a ring. */}
        <div className="card flex items-center gap-4 p-4">
          <RadialRing
            percent={data.total_transactions > 0 ? (tierCounts.HIGH / data.total_transactions) * 100 : 0}
            color={RISK_TIER_COLOR.HIGH}
            size={72}
            strokeWidth={7}
            label={
              <span className="font-mono text-sm font-semibold tabular-nums text-risk-high">
                {formatPercent(tierCounts.HIGH, data.total_transactions)}
              </span>
            }
          />
          <div>
            <div className="text-sm text-text-secondary">HIGH-tier count</div>
            <div className="font-mono text-lg font-semibold tabular-nums text-text-primary">
              {tierCounts.HIGH.toLocaleString()}
            </div>
          </div>
        </div>
        <StatCard
          label="Fraud rate among HIGH tier"
          value={data.high_tier_fraud_rate === null ? 'N/A' : `${(data.high_tier_fraud_rate * 100).toFixed(1)}%`}
          caption={data.high_tier_fraud_rate === null ? data.high_tier_fraud_rate_note : undefined}
        />
      </div>

      <div className="card p-6">
        <h2 className="font-display text-base font-semibold text-text-primary">Risk tier distribution</h2>
        <RiskTierBarChart counts={tierCounts} />
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

      <div className="card p-6">
        <h2 className="font-display text-base font-semibold text-text-primary">Decisions</h2>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
          {DECISIONS.map((decision) => (
            <StatCard
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
    <div className="space-y-8 animate-pulse">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-24 rounded-2xl border border-border bg-bg-surface-raised" />
        ))}
      </div>
      <div className="h-72 rounded-2xl border border-border bg-bg-surface-raised" />
    </div>
  );
}
