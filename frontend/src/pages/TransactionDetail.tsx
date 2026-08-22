import { Link, useParams } from 'react-router-dom';
import { ApiError, getTransaction } from '../api/client';
import { useApiData } from '../api/hooks';
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/AsyncState';
import { DecisionBadge, RiskTierBadge } from '../components/Badge';
import { StatCard } from '../components/StatCard';
import type { PredictionOut, ShapFeatureContribution } from '../types/api';
import { formatAmount, formatProbability, formatTimestamp } from '../utils/format';

function FeatureRow({ contribution }: { contribution: ShapFeatureContribution }) {
  return (
    <li className="flex items-baseline justify-between gap-4 py-1.5 text-sm">
      <span className="text-[#0b0b0b]">{contribution.label}</span>
      <span className="shrink-0 font-mono text-xs text-[#898781]">
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
        <Link to="/high-risk" className="text-sm text-[#52514e] hover:text-[#0b0b0b]">
          &larr; Back to High-Risk Transactions
        </Link>
        <h1 className="mt-2 font-mono text-lg font-semibold break-all text-[#0b0b0b]">{data.transaction_id}</h1>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Amount" value={formatAmount(data.amount)} />
        <StatCard label="Fraud probability" value={formatProbability(data.fraud_probability)} />
        <StatCard label="Expected loss" value={formatAmount(data.expected_loss)} />
        <StatCard label="Model version" value={data.model_version} />
      </div>

      <div className="flex flex-wrap items-center gap-4 rounded-lg border border-[#e1e0d9] bg-[#fcfcfb] p-4">
        <span className="text-sm text-[#52514e]">Risk tier</span>
        <RiskTierBadge tier={data.risk_tier} />
        <span className="text-sm text-[#52514e]">Decision</span>
        <DecisionBadge decision={data.decision} />
        <span className="ml-auto text-sm text-[#898781]">{formatTimestamp(data.timestamp)}</span>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-[#e1e0d9] bg-[#fcfcfb] p-6">
          <h2 className="text-base font-semibold text-[#d03b3b]">Top risk factors</h2>
          <p className="mt-1 text-xs text-[#898781]">Pushed this transaction toward a higher fraud probability.</p>
          {top_positive_features.length === 0 ? (
            <p className="mt-3 text-sm text-[#52514e]">No strong risk-increasing factors identified.</p>
          ) : (
            <ul className="mt-3 divide-y divide-[#e1e0d9]">
              {top_positive_features.map((contribution) => (
                <FeatureRow key={contribution.feature} contribution={contribution} />
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-lg border border-[#e1e0d9] bg-[#fcfcfb] p-6">
          <h2 className="text-base font-semibold text-[#0ca30c]">Risk-reducing factors</h2>
          <p className="mt-1 text-xs text-[#898781]">Pushed this transaction toward being legitimate.</p>
          {top_negative_features.length === 0 ? (
            <p className="mt-3 text-sm text-[#52514e]">No strong risk-reducing factors identified.</p>
          ) : (
            <ul className="mt-3 divide-y divide-[#e1e0d9]">
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
