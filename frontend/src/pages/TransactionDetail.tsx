import { Link, useParams } from 'react-router-dom';
import { ApiError, getTransaction } from '../api/client';
import { useApiData } from '../api/hooks';
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/AsyncState';
import { DecisionBadge, RiskTierBadge } from '../components/Badge';
import { RadialRing } from '../components/RadialRing';
import { StatCard } from '../components/StatCard';
import { Tooltip, TooltipContent, TooltipTrigger } from '../components/ui/tooltip';
import { useCountUp, useSweepInOnMount } from '../hooks/useCountUp';
import { RISK_TIER_COLOR, RISK_TIER_COLOR_ON_DARK } from '../theme/colors';
import type { PredictionOut, ShapFeatureContribution } from '../types/api';
import { formatAmount, formatTimestamp } from '../utils/format';

/** SHAP row: the value itself already shows on the row; the tooltip adds
 * the raw contribution MAGNITUDE (the model's internal log-odds push),
 * which previously had nowhere to show without cluttering the row --
 * see the design plan's component-sourcing section. */
function FeatureRow({ contribution }: { contribution: ShapFeatureContribution }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <li className="flex cursor-default items-baseline justify-between gap-4 rounded-(--radius-control) px-1 py-1.5 text-sm transition-colors duration-100 hover:bg-bg-surface-raised">
          <span className="text-text-primary">{contribution.label}</span>
          <span className="shrink-0 font-mono text-xs tabular-nums text-text-muted">
            value {contribution.feature_value.toFixed(3)}
          </span>
        </li>
      </TooltipTrigger>
      <TooltipContent side="left">
        <span className="font-mono tabular-nums">SHAP contribution: {contribution.shap_value.toFixed(4)}</span>
      </TooltipContent>
    </Tooltip>
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

  return <TransactionDetailBody data={result.data} />;
}

/** Split out so the signature-element hooks below only ever mount once
 * real data exists -- see Dashboard.tsx's DashboardBody for the same
 * rules-of-hooks reasoning against TransactionDetail()'s early returns. */
function TransactionDetailBody({ data }: { data: PredictionOut }) {
  const { top_positive_features, top_negative_features } = data.shap_explanation;
  const fraudProbabilityPercent = data.fraud_probability * 100;
  const animatedRingPercent = useSweepInOnMount(fraudProbabilityPercent);
  const animatedRingLabelPercent = useCountUp(fraudProbabilityPercent);

  return (
    <div className="space-y-8">
      <div className="card-dark p-6">
        <Link
          to="/high-risk"
          className="rounded text-sm text-text-secondary hover:text-text-primary focus-visible:outline-2 focus-visible:outline-[var(--color-text-primary-on-dark)] focus-visible:outline-offset-2"
        >
          &larr; Back to High-Risk Transactions
        </Link>
        <h1 className="mt-2 font-mono text-lg font-semibold break-all text-text-primary">{data.transaction_id}</h1>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard onDark label="Amount" value={formatAmount(data.amount)} />
        {/* Hero single-value metric -> radial ring (see the design plan:
            hero stats with dedicated space get the ring, dense table
            rows keep the horizontal RiskMeter). Ring color is always the
            real tier color, never violet -- see RadialRing's docstring.
            Sweeps in + counts up on load -- the design plan's signature
            element -- driven by the same real fraud_probability either way. */}
        <div className="card-dark flex items-center gap-4 p-4">
          <RadialRing
            percent={animatedRingPercent}
            color={RISK_TIER_COLOR[data.risk_tier]}
            size={72}
            strokeWidth={7}
            label={
              <span className="font-mono text-sm font-semibold tabular-nums" style={{ color: RISK_TIER_COLOR_ON_DARK[data.risk_tier] }}>
                {animatedRingLabelPercent.toFixed(1)}%
              </span>
            }
          />
          <div className="text-sm text-text-secondary">Fraud probability</div>
        </div>
        <StatCard onDark label="Expected loss" value={formatAmount(data.expected_loss)} />
        <StatCard onDark label="Model version" value={data.model_version} />
      </div>

      <div className="card-dark flex flex-wrap items-center gap-4 p-4">
        <span className="text-sm text-text-secondary">Risk tier</span>
        <RiskTierBadge tier={data.risk_tier} onDark />
        <span className="text-sm text-text-secondary">Decision</span>
        <DecisionBadge decision={data.decision} onDark />
        <span className="ml-auto font-mono text-sm text-text-muted">{formatTimestamp(data.timestamp)}</span>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="card-dark p-6">
          <h2 className="font-display text-base font-semibold text-accent-on-dark">Top risk factors</h2>
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

        <div className="card-dark p-6">
          <h2 className="font-display text-base font-semibold text-text-secondary-on-dark">Risk-reducing factors</h2>
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
