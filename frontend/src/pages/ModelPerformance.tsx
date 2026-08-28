import { getDriftReport, getModelInfo, getReturnModelInfo } from '../api/client';
import { useApiData } from '../api/hooks';
import { ConfusionMatrix } from '../components/ConfusionMatrix';
import { DriftMonitor } from '../components/DriftMonitor';
import { ErrorBlock, LoadingBlock } from '../components/AsyncState';
import { StatCard } from '../components/StatCard';
import type { DriftReportOut, ModelInfoOut, ReturnModelInfoOut } from '../types/api';
import { formatTimestamp } from '../utils/format';

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

/** Tier 2's return-risk model, in its own clearly-separated section --
 * never merged into the fraud model's stat cards above, and never
 * described as coming from the same dataset. See
 * api/services/return_model_info_service.py's DATASET_HONESTY_NOTE for
 * why this model's numbers get an explicit caution banner the fraud
 * model's don't.
 */
function ReturnModelSection() {
  const returnModelInfo = useApiData<ReturnModelInfoOut>(getReturnModelInfo);

  if (returnModelInfo.status === 'loading') return <LoadingBlock />;
  if (returnModelInfo.status === 'error') {
    return <ErrorBlock message={returnModelInfo.error.message} onRetry={returnModelInfo.refetch} />;
  }

  const data = returnModelInfo.data;

  return (
    <div className="space-y-6 border-t border-border pt-8">
      <div>
        <h1 className="font-display text-lg font-semibold text-text-primary">Return-Risk Model (Tier 2)</h1>
        <p className="mt-1 max-w-2xl text-sm text-text-secondary">
          A completely separate model, trained on a completely separate dataset from the fraud model above --{' '}
          <strong className="text-text-primary">{data.dataset_version}</strong>, not the fraud model's ULB/Kaggle
          credit-card dataset. Held-out TEST-set performance, same discipline as above: nothing here was tuned
          against the test set.
        </p>
      </div>

      {/* Standing disclosure, not a live alert -- weight (thicker border)
          carries the emphasis, not the reserved accent colors. */}
      <div className="rounded-xl border-2 border-text-primary bg-bg-surface-raised p-4 text-sm text-text-primary">
        <strong>Read this before trusting these numbers like the fraud model's:</strong> {data.dataset_honesty_note}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Model version" value={data.model_version} caption={data.model_name} />
        <StatCard label="Training date" value={formatTimestamp(data.training_date)} />
        <StatCard label="Dataset" value={data.dataset_version} compact />
        <StatCard label="Classification threshold" value={data.threshold.toFixed(2)} />
      </div>

      <div className="card p-6">
        <h2 className="font-display text-base font-semibold text-text-primary">Test-set metrics</h2>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Precision" value={formatPercent(data.precision)} />
          <StatCard label="Recall" value={formatPercent(data.recall)} />
          <StatCard label="F1 score" value={data.f1.toFixed(4)} />
          <StatCard label="PR-AUC" value={data.pr_auc.toFixed(4)} />
          <StatCard label="ROC-AUC" value={data.roc_auc.toFixed(4)} />
          <StatCard label="False positive rate" value={formatPercent(data.false_positive_rate)} />
          <StatCard label="False negative rate" value={formatPercent(data.false_negative_rate)} />
          <StatCard label="Test set size" value={data.test_set_size.toLocaleString()} />
        </div>
      </div>

      <div className="card p-6">
        <h2 className="font-display text-base font-semibold text-text-primary">Confusion matrix</h2>
        <p className="mt-1 text-xs text-text-muted">
          {data.test_set_size.toLocaleString()} held-out test orders, at threshold {data.threshold.toFixed(2)}.
        </p>
        <div className="mt-4">
          <ConfusionMatrix tp={data.tp} fp={data.fp} fn={data.fn} tn={data.tn} positiveLabel="Returned" negativeLabel="Not returned" />
        </div>
      </div>
    </div>
  );
}

/** Tier 3B's drift monitor, in its own independently-loading section --
 * same pattern as ReturnModelSection above: it must never block or be
 * blocked by the fraud model's own stat cards rendering, since the two
 * come from separate endpoints with separate failure modes.
 */
function DriftMonitorSection() {
  const driftReport = useApiData<DriftReportOut>(getDriftReport);

  if (driftReport.status === 'loading') return <LoadingBlock />;
  if (driftReport.status === 'error') {
    return <ErrorBlock message={driftReport.error.message} onRetry={driftReport.refetch} />;
  }

  return <DriftMonitor report={driftReport.data} />;
}

export function ModelPerformance() {
  const modelInfo = useApiData<ModelInfoOut>(getModelInfo);

  if (modelInfo.status === 'loading') return <LoadingBlock />;
  if (modelInfo.status === 'error') {
    return <ErrorBlock message={modelInfo.error.message} onRetry={modelInfo.refetch} />;
  }

  const data = modelInfo.data;

  return (
    <div className="space-y-8">
      <div className="card p-6">
        <h1 className="font-display text-lg font-semibold text-text-primary">Model Performance</h1>
        <p className="mt-1 max-w-2xl text-sm text-text-secondary">
          <strong className="text-text-primary">Held-out TEST-set performance</strong> -- the final, once-only
          evaluation split the model never saw during training or threshold tuning (see the Day 5 audit). This is
          different from validation numbers shown elsewhere during development, and different again from the
          live/simulated traffic on the Dashboard and Fraud Spike pages.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Model version" value={data.model_version} caption={data.model_name} />
        <StatCard label="Training date" value={formatTimestamp(data.training_date)} />
        <StatCard label="Dataset" value={data.dataset_version} compact />
        <StatCard label="Classification threshold" value={data.threshold.toFixed(2)} />
      </div>

      <div className="card p-6">
        <h2 className="font-display text-base font-semibold text-text-primary">Test-set metrics</h2>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Precision" value={formatPercent(data.precision)} />
          <StatCard label="Recall" value={formatPercent(data.recall)} />
          <StatCard label="F1 score" value={data.f1.toFixed(4)} />
          <StatCard label="PR-AUC" value={data.pr_auc.toFixed(4)} />
          <StatCard label="ROC-AUC" value={data.roc_auc.toFixed(4)} />
          <StatCard label="False positive rate" value={formatPercent(data.false_positive_rate)} />
          <StatCard label="False negative rate" value={formatPercent(data.false_negative_rate)} />
          <StatCard label="Test set size" value={data.test_set_size.toLocaleString()} />
        </div>
      </div>

      <div className="card p-6">
        <h2 className="font-display text-base font-semibold text-text-primary">Confusion matrix</h2>
        <p className="mt-1 text-xs text-text-muted">
          {data.test_set_size.toLocaleString()} held-out test transactions, at threshold {data.threshold.toFixed(2)}.
        </p>
        <div className="mt-4">
          <ConfusionMatrix tp={data.tp} fp={data.fp} fn={data.fn} tn={data.tn} />
        </div>
      </div>

      <div className="card p-4 text-sm text-text-secondary">
        <strong className="text-text-primary">A note on what's real vs. simulated:</strong> this page's numbers
        come from the actual, audited held-out test set -- real historical transactions, scored once, never
        touched for tuning. The <strong className="text-text-primary">Dashboard</strong>,{' '}
        <strong className="text-text-primary">High-Risk Transactions</strong>, and{' '}
        <strong className="text-text-primary">Fraud Spike</strong> pages instead show predictions made during this
        demo session -- either replayed real transactions from{' '}
        <code className="rounded bg-bg-surface-raised px-1 py-0.5 text-xs">simulator/simulate.py</code> or manual
        API calls. Both are genuine model outputs on real transaction data; neither is fabricated. But they answer
        different questions -- this page answers "how good is the model," the others answer "what is happening
        right now" -- and the two should never be quoted interchangeably.
      </div>

      <ReturnModelSection />
      <DriftMonitorSection />
    </div>
  );
}
