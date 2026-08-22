import { Link, useParams } from 'react-router-dom';
import { ApiError, getChargebackEvidence } from '../api/client';
import { useApiData } from '../api/hooks';
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/AsyncState';
import { DecisionBadge, FlaggedInAdvanceBadge, RiskTierBadge } from '../components/Badge';
import { StatCard } from '../components/StatCard';
import { SEVERITY_COLOR } from '../theme/colors';
import type { EvidencePackageOut, TimelineEventOut } from '../types/api';
import { formatAmount, formatProbability, formatTimestamp } from '../utils/format';

function TimelineRow({ event, isLast }: { event: TimelineEventOut; isLast: boolean }) {
  return (
    <li className="relative pb-6 pl-6 last:pb-0">
      {!isLast && <span className="absolute top-2 left-[3px] h-full w-px bg-[#e1e0d9]" />}
      <span className="absolute top-1.5 left-0 h-2 w-2 rounded-full bg-[#898781]" />
      <div className="text-xs text-[#898781]">
        {event.timestamp ? formatTimestamp(event.timestamp) : 'no timestamp available'}
      </div>
      <div className="mt-0.5 text-sm text-[#0b0b0b]">{event.description}</div>
    </li>
  );
}

export function ChargebackDetail() {
  const { id } = useParams<{ id: string }>();
  const result = useApiData<EvidencePackageOut>(() => getChargebackEvidence(id ?? ''), [id]);

  if (result.status === 'loading') return <LoadingBlock />;

  if (result.status === 'error') {
    if (result.error instanceof ApiError && result.error.status === 404) {
      return (
        <EmptyBlock
          title="Chargeback not found"
          description={`No chargeback matches id "${id}". Check the id and try again.`}
        />
      );
    }
    return <ErrorBlock message={result.error.message} onRetry={result.refetch} />;
  }

  const data = result.data;
  const { summary, transaction, refund } = data;
  const bannerColor = summary.was_flagged_in_advance ? SEVERITY_COLOR.NONE : SEVERITY_COLOR.HIGH;

  return (
    <div className="space-y-8">
      <div>
        <Link to="/chargebacks" className="text-sm text-[#52514e] hover:text-[#0b0b0b]">
          &larr; Back to Chargeback Evidence Center
        </Link>
        <h1 className="mt-2 font-mono text-lg font-semibold break-all text-[#0b0b0b]">{data.chargeback.chargeback_id}</h1>
        <p className="mt-1 text-xs text-[#898781]">
          Transaction: <span className="font-mono">{data.chargeback.transaction_id}</span>
        </p>
      </div>

      <div className="rounded-lg border-2 p-6" style={{ borderColor: bannerColor, backgroundColor: `${bannerColor}0d` }}>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <p className="max-w-2xl text-sm text-[#0b0b0b]">{summary.narrative}</p>
          <FlaggedInAdvanceBadge
            flagged={summary.was_flagged_in_advance}
            hasData={summary.risk_tier_at_scoring !== null}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Chargeback amount" value={formatAmount(data.chargeback.amount)} caption={data.chargeback.reason} />
        <StatCard label="Chargeback status" value={data.chargeback.status} />
        <StatCard
          label="Fraud probability at scoring"
          value={summary.fraud_probability_at_scoring !== null ? formatProbability(summary.fraud_probability_at_scoring) : 'no data'}
        />
        <StatCard label="Refund on file" value={refund ? formatAmount(refund.amount) : 'none'} caption={refund?.reason} />
      </div>

      {transaction && (
        <div className="flex flex-wrap items-center gap-4 rounded-lg border border-[#e1e0d9] bg-[#fcfcfb] p-4">
          <span className="text-sm text-[#52514e]">Risk tier at scoring</span>
          <RiskTierBadge tier={transaction.risk_tier} />
          <span className="text-sm text-[#52514e]">Decision at scoring</span>
          <DecisionBadge decision={transaction.decision} />
          <span className="ml-auto text-sm text-[#898781]">Customer: {data.customer}</span>
        </div>
      )}

      <div className="rounded-lg border border-[#e1e0d9] bg-[#fcfcfb] p-6">
        <h2 className="text-base font-semibold text-[#0b0b0b]">Evidence timeline</h2>
        <ol className="mt-4">
          {data.timeline.map((event, index) => (
            <TimelineRow key={`${event.event}-${index}`} event={event} isLast={index === data.timeline.length - 1} />
          ))}
        </ol>
      </div>

      <div className="rounded-lg border border-[#e1e0d9] bg-[#fcfcfb] p-4 text-xs text-[#898781]">{data.data_model_note}</div>
    </div>
  );
}
