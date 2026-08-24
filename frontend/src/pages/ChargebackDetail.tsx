import { Link, useParams } from 'react-router-dom';
import { ApiError, getChargebackEvidence } from '../api/client';
import { useApiData } from '../api/hooks';
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/AsyncState';
import { DecisionBadge, FlaggedInAdvanceBadge, RiskTierBadge } from '../components/Badge';
import { RadialRing } from '../components/RadialRing';
import { StatCard } from '../components/StatCard';
import { useCountUp, useSweepInOnMount } from '../hooks/useCountUp';
import { RISK_TIER_COLOR, RISK_TIER_COLOR_ON_DARK, SEVERITY_COLOR } from '../theme/colors';
import type { AutoSummaryOut, EvidencePackageOut, RiskTier, TimelineEventOut } from '../types/api';
import { formatAmount, formatTimestamp } from '../utils/format';

/** Its own component (not inlined) purely so the signature-element hooks
 * can be called unconditionally within it -- this whole block only
 * mounts at all when fraud_probability_at_scoring exists, which is fine;
 * hooks rules only forbid calling them conditionally WITHIN one
 * component's render, not gating whether the component mounts. */
function AnimatedFraudProbabilityRing({ probability, tier }: { probability: number; tier: RiskTier }) {
  const percent = probability * 100;
  const animatedRingPercent = useSweepInOnMount(percent);
  const animatedRingLabelPercent = useCountUp(percent);
  return (
    <RadialRing
      percent={animatedRingPercent}
      color={RISK_TIER_COLOR[tier]}
      size={72}
      strokeWidth={7}
      label={
        // Card below is always card-dark now -- the arc keeps the plain
        // tier color (non-text, already clears 3:1), the label text uses
        // the on-dark variant (needs 4.5:1) -- same split as Dashboard's
        // ring. See theme/colors.ts's RISK_TIER_COLOR_ON_DARK.
        <span className="font-mono text-sm font-semibold tabular-nums" style={{ color: RISK_TIER_COLOR_ON_DARK[tier] }}>
          {animatedRingLabelPercent.toFixed(1)}%
        </span>
      }
    />
  );
}

/** Renders src/evidence/summarize_evidence.py's output -- a narrative
 * built by fixed Python string templates from facts shown elsewhere on
 * this page, NOT an LLM call. Labeled honestly as "Automated summary,"
 * and never presented as additional evidence beyond the timeline/records
 * below it. `available: false` is an expected, non-error state; the page
 * must still be fully usable either way.
 */
function AutoSummaryBlock({ autoSummary }: { autoSummary: AutoSummaryOut }) {
  if (!autoSummary.available || !autoSummary.text) {
    return (
      <div className="card-dark border-dashed p-4 text-xs text-text-muted">
        Automated summary unavailable right now -- see the evidence records below for the full picture.
      </div>
    );
  }

  return (
    <div className="card-dark bg-bg-surface-raised p-4">
      <div className="text-xs font-medium tracking-wide text-text-muted uppercase">Automated summary</div>
      <p className="mt-2 text-sm text-text-primary">{autoSummary.text}</p>
      <p className="mt-2 text-xs text-text-muted">
        Generated automatically by fixed rules from the records shown below -- not written by a person, and not
        additional evidence beyond what's already on this page.
      </p>
    </div>
  );
}

function TimelineRow({ event, isLast }: { event: TimelineEventOut; isLast: boolean }) {
  return (
    <li className="relative pb-6 pl-6 last:pb-0">
      {!isLast && <span className="absolute top-2 left-[3px] h-full w-px bg-border" />}
      <span className="absolute top-1.5 left-0 h-2 w-2 rounded-full bg-text-muted" />
      <div className="font-mono text-xs text-text-muted">
        {event.timestamp ? formatTimestamp(event.timestamp) : 'no timestamp available'}
      </div>
      <div className="mt-0.5 text-sm text-text-primary">{event.description}</div>
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
      <div className="card-dark p-6">
        <Link
          to="/chargebacks"
          className="rounded text-sm text-text-secondary hover:text-text-primary focus-visible:outline-2 focus-visible:outline-[var(--color-text-primary-on-dark)] focus-visible:outline-offset-2"
        >
          &larr; Back to Chargeback Evidence Center
        </Link>
        <h1 className="mt-2 font-mono text-lg font-semibold break-all text-text-primary">{data.chargeback.chargeback_id}</h1>
        <p className="mt-1 text-xs text-text-muted">
          Transaction: <span className="font-mono">{data.chargeback.transaction_id}</span>
        </p>
      </div>

      <AutoSummaryBlock autoSummary={data.auto_summary} />

      <div className="rounded-(--radius-card) border-2 p-6" style={{ borderColor: bannerColor, backgroundColor: `${bannerColor}1a` }}>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <p className="max-w-2xl text-sm text-text-primary">{summary.narrative}</p>
          <FlaggedInAdvanceBadge
            flagged={summary.was_flagged_in_advance}
            hasData={summary.risk_tier_at_scoring !== null}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard onDark label="Chargeback amount" value={formatAmount(data.chargeback.amount)} caption={data.chargeback.reason} />
        <StatCard onDark label="Chargeback status" value={data.chargeback.status} />
        <div className="card-dark flex items-center gap-4 p-4">
          {summary.fraud_probability_at_scoring !== null && summary.risk_tier_at_scoring !== null ? (
            <>
              <AnimatedFraudProbabilityRing
                probability={summary.fraud_probability_at_scoring}
                tier={summary.risk_tier_at_scoring}
              />
              <div className="text-sm text-text-secondary">Fraud probability at scoring</div>
            </>
          ) : (
            <div>
              <div className="text-sm text-text-secondary">Fraud probability at scoring</div>
              <span className="font-mono text-2xl font-semibold text-text-primary">no data</span>
            </div>
          )}
        </div>
        <StatCard onDark label="Refund on file" value={refund ? formatAmount(refund.amount) : 'none'} caption={refund?.reason} />
      </div>

      {transaction && (
        <div className="card-dark flex flex-wrap items-center gap-4 p-4">
          <span className="text-sm text-text-secondary">Risk tier at scoring</span>
          <RiskTierBadge tier={transaction.risk_tier} onDark />
          <span className="text-sm text-text-secondary">Decision at scoring</span>
          <DecisionBadge decision={transaction.decision} onDark />
          <span className="ml-auto text-sm text-text-muted">Customer: {data.customer}</span>
        </div>
      )}

      <div className="card-dark p-6">
        <h2 className="font-display text-base font-semibold text-text-primary">Evidence timeline</h2>
        <ol className="mt-4">
          {data.timeline.map((event, index) => (
            <TimelineRow key={`${event.event}-${index}`} event={event} isLast={index === data.timeline.length - 1} />
          ))}
        </ol>
      </div>

      <div className="card-dark p-4 text-xs text-text-muted">{data.data_model_note}</div>
    </div>
  );
}
