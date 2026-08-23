import { Link, useParams } from 'react-router-dom';
import { ApiError, getTransaction } from '../api/client';
import { useApiData } from '../api/hooks';
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/AsyncState';
import { DecisionBadge, RiskTierBadge } from '../components/Badge';
import { RiskMeter } from '../components/RiskMeter';
import { StatCard } from '../components/StatCard';
import type { PredictionOut, ShapFeatureContribution } from '../types/api';
import { formatAmount, formatTimestamp } from '../utils/format';

function FeatureRow({ contribution }: { contribution: ShapFeatureContribution }) {
  return (
    <li className="flex items-baseline justify-between gap-4 py-1.5 text-sm">
      <span className="text-text-primary">{contribution.label}</span>
      <span className="shrink-0 font-mono text-xs tabular-nums text-text-muted">
        value {contribution.feature_value.toFixed(3)}
      </span>
    </li>
  );
}

export function TransactionDetail() {
  const { id } = useParams<{ id: string }>();
  const result = useApiData<PredictionOut>(() => getTransaction(id ?? ''), [id]);

  if (result.status === 'loading') return <LoadingBlock />;

  if (result.status === 'error') {
    if (result.error instanceof ApiError && result.error.status === 404) {
      return (
        <EmptyBlock
          title="Transaction not found"
          description={`No scored transaction matches id "${id}". Check the id and try again.`}
        />
      );
    }
    return <ErrorBlock message={result.error.message} onRetry={result.refetch} />;
  }

  const data = result.data;
  const { top_positive_features, top_negative_features } = data.shap_explanation;

  return (
    <div className="space-y-8">
      <div>
        <Link
          to="/high-risk"
          className="rounded text-sm text-text-secondary hover:text-text-primary focus-visible:outline-2 focus-visible:outline-[var(--color-accent)] focus-visible:outline-offset-2"
        >
          &larr; Back to High-Risk Transactions
        </Link>
        <h1 className="mt-2 font-mono text-lg font-semibold break-all text-text-primary">{data.transaction_id}</h1>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Amount" value={formatAmount(data.amount)} />
        <div className="rounded-lg border border-border bg-bg-surface p-4">
          <div className="text-sm text-text-secondary">Fraud probability</div>
          <div className="mt-2">
            <RiskMeter probability={data.fraud_probability} tier={data.risk_tier} />
          </div>
        </div>
        <StatCard label="Expected loss" value={formatAmount(data.expected_loss)} />
        <StatCard label="Model version" value={data.model_version} />
      </div>

      <div className="flex flex-wrap items-center gap-4 rounded-lg border border-border bg-bg-surface p-4">
        <span className="text-sm text-text-secondary">Risk tier</span>
        <RiskTierBadge tier={data.risk_tier} />
        <span className="text-sm text-text-secondary">Decision</span>
        <DecisionBadge decision={data.decision} />
        <span className="ml-auto font-mono text-sm text-text-muted">{formatTimestamp(data.timestamp)}</span>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-border bg-bg-surface p-6">
          <h2 className="font-display text-base font-semibold text-risk-high">Top risk factors</h2>
          <p className="mt-1 text-xs text-text-muted">Pushed this transaction toward a higher fraud probability.</p>
          {top_positive_features.length === 0 ? (
            <p className="mt-3 text-sm text-text-secondary">No strong risk-increasing factors identified.</p>
          ) : (
            <ul className="mt-3 divide-y divide-border">
              {top_positive_features.map((contribution) => (
                <FeatureRow key={contribution.feature} contribution={contribution} />
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-lg border border-border bg-bg-surface p-6">
          <h2 className="font-display text-base font-semibold text-risk-low">Risk-reducing factors</h2>
          <p className="mt-1 text-xs text-text-muted">Pushed this transaction toward being legitimate.</p>
          {top_negative_features.length === 0 ? (
            <p className="mt-3 text-sm text-text-secondary">No strong risk-reducing factors identified.</p>
          ) : (
            <ul className="mt-3 divide-y divide-border">
              {top_negative_features.map((contribution) => (
                <FeatureRow key={contribution.feature} contribution={contribution} />
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
