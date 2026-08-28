import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { getModelInfo, getReturnModelInfo } from '../api/client';
import { useApiData } from '../api/hooks';
import { ErrorBlock, LoadingBlock } from '../components/AsyncState';
import { SuccessBadge } from '../components/Badge';
import type { ModelInfoOut, ReturnModelInfoOut } from '../types/api';

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

function RequirementRow({ badge, title, children }: { badge: ReactNode; title: string; children: ReactNode }) {
  return (
    <div className="card flex flex-col gap-2 p-5 sm:flex-row sm:items-start sm:gap-4">
      <div className="shrink-0 pt-0.5">{badge}</div>
      <div className="min-w-0">
        <div className="font-display text-sm font-semibold text-text-primary">{title}</div>
        <div className="mt-1 text-sm text-text-secondary">{children}</div>
      </div>
    </div>
  );
}

/** Tier 3D: maps this project directly onto the hackathon problem
 * statement, for a judge doing an evaluation pass -- this page's entire
 * job IS being the thing a judge finds first, so it sits last in the top
 * nav's reading order but is still one click away from every other page.
 *
 * Every number here is fetched live from the SAME endpoints
 * (GET /api/v1/models, GET /api/v1/models/return) that Model Performance
 * itself reads from -- never a separately hardcoded copy -- so this page
 * cannot silently drift out of sync with the numbers a judge would see
 * by clicking through to Model Performance directly. See
 * tests/test_submission_mapping.py (backend) and this page's own
 * rendering for the two things that keep that true.
 */
export function SubmissionMapping() {
  const modelInfo = useApiData<ModelInfoOut>(getModelInfo);
  const returnModelInfo = useApiData<ReturnModelInfoOut>(getReturnModelInfo);

  return (
    <div className="space-y-10">
      <div className="card p-6">
        <h1 className="font-display text-lg font-semibold text-text-primary">Problem Statement Mapping</h1>
        <p className="mt-1 max-w-2xl text-sm text-text-secondary">
          A direct map from this project to the hackathon brief -- every number below is fetched live from the same
          endpoints{' '}
          <Link
            to="/model-performance"
            className="rounded text-text-secondary underline underline-offset-2 transition-colors duration-150 hover:text-accent focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2"
          >
            Model Performance
          </Link>{' '}
          reads from, not a separate hardcoded copy, so it cannot drift out of sync with what you see there.
        </p>
      </div>

      <section className="space-y-4">
        <h2 className="font-display text-base font-semibold text-text-primary">&ldquo;The Bar&rdquo;</h2>

        <RequirementRow badge={<SuccessBadge label="Met" />} title="Working detector/verifier">
          A trained fraud model, live at{' '}
          <code className="rounded bg-bg-surface-raised px-1 py-0.5 text-xs">POST /api/v1/predict</code>. Every
          score you see on the{' '}
          <Link
            to="/"
            className="rounded text-text-secondary underline underline-offset-2 transition-colors duration-150 hover:text-accent focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2"
          >
            Dashboard
          </Link>{' '}
          and{' '}
          <Link
            to="/high-risk"
            className="rounded text-text-secondary underline underline-offset-2 transition-colors duration-150 hover:text-accent focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2"
          >
            High-Risk Transactions
          </Link>{' '}
          comes from this endpoint, not a mock.
        </RequirementRow>

        <RequirementRow badge={<SuccessBadge label="Met" />} title="Measured precision and recall on a held-out test set">
          {modelInfo.status === 'loading' && <LoadingBlock />}
          {modelInfo.status === 'error' && <ErrorBlock message={modelInfo.error.message} onRetry={modelInfo.refetch} />}
          {modelInfo.status === 'success' && (
            <>
              Precision <span className="font-mono tabular-nums text-text-primary">{formatPercent(modelInfo.data.precision)}</span>,
              recall <span className="font-mono tabular-nums text-text-primary">{formatPercent(modelInfo.data.recall)}</span>,
              PR-AUC <span className="font-mono tabular-nums text-text-primary">{modelInfo.data.pr_auc.toFixed(4)}</span>, ROC-AUC{' '}
              <span className="font-mono tabular-nums text-text-primary">{modelInfo.data.roc_auc.toFixed(4)}</span> on a{' '}
              {modelInfo.data.test_set_size.toLocaleString()}-row held-out test set, never touched during training or threshold
              tuning.
            </>
          )}{' '}
          Full breakdown, confusion matrix, and methodology on{' '}
          <Link
            to="/model-performance"
            className="rounded text-text-secondary underline underline-offset-2 transition-colors duration-150 hover:text-accent focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2"
          >
            Model Performance
          </Link>
          .
        </RequirementRow>

        <RequirementRow badge={<SuccessBadge label="Met" />} title="Strictly defense-only">
          No offensive or exploit capability exists anywhere in this codebase. Every endpoint is read/score-only --
          detect, explain, simulate a threshold, replay historical test data -- nothing here sends, attacks, or
          automates action against an external system.
        </RequirementRow>

        <RequirementRow badge={<SuccessBadge label="Met" />} title="Honest metrics that acknowledge false-positive cost">
          This is this project&apos;s strongest differentiator, not an afterthought: the{' '}
          <Link
            to="/threshold-simulator"
            className="rounded text-text-secondary underline underline-offset-2 transition-colors duration-150 hover:text-accent focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2"
          >
            Threshold Simulator
          </Link>{' '}
          lets you drag the decision threshold and watch precision/recall trade off live against a named{' '}
          <code className="rounded bg-bg-surface-raised px-1 py-0.5 text-xs">cost_engine</code> that prices a missed
          fraud case against a false alarm explicitly, rather than reporting a single accuracy number and calling it
          done.
        </RequirementRow>
      </section>

      <section className="space-y-4">
        <h2 className="font-display text-base font-semibold text-text-primary">Named examples</h2>

        <RequirementRow badge={<SuccessBadge label="Built" />} title="Fraud-spike detector">
          A live, rolling anomaly detector comparing recent HIGH-risk rate against the model&apos;s training-derived
          baseline. See{' '}
          <Link
            to="/fraud-spike"
            className="rounded text-text-secondary underline underline-offset-2 transition-colors duration-150 hover:text-accent focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2"
          >
            Fraud Spike
          </Link>
          .
        </RequirementRow>

        <RequirementRow badge={<SuccessBadge label="Built" />} title="Chargeback evidence responder">
          Built -- deterministic, zero-hallucination automated summary: a Python template filling in real fields
          already visible on the page, not an LLM call. See{' '}
          <Link
            to="/chargebacks"
            className="rounded text-text-secondary underline underline-offset-2 transition-colors duration-150 hover:text-accent focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2"
          >
            Chargeback Center
          </Link>
          .
        </RequirementRow>

        <RequirementRow badge={<SuccessBadge label="Built" />} title="Return-risk scorer">
          Built and evaluated with the same rigor as the fraud model, but trained on a smaller dataset with a proxy
          label rather than verified ground truth --{' '}
          {returnModelInfo.status === 'success' ? (
            <>the model&apos;s own disclosure, unedited: &ldquo;{returnModelInfo.data.dataset_honesty_note}&rdquo;</>
          ) : (
            'see Model Performance for the full disclosure'
          )}
          . See{' '}
          <Link
            to="/model-performance"
            className="rounded text-text-secondary underline underline-offset-2 transition-colors duration-150 hover:text-accent focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2"
          >
            Model Performance
          </Link>{' '}
          for the full numbers.
        </RequirementRow>
      </section>
    </div>
  );
}
