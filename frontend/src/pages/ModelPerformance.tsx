import { getModelInfo } from '../api/client';
import { useApiData } from '../api/hooks';
import { ConfusionMatrix } from '../components/ConfusionMatrix';
import { ErrorBlock, LoadingBlock } from '../components/AsyncState';
import { StatCard } from '../components/StatCard';
import type { ModelInfoOut } from '../types/api';
import { formatTimestamp } from '../utils/format';

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
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
      <div>
        <h1 className="text-lg font-semibold text-[#0b0b0b]">Model Performance</h1>
        <p className="mt-1 max-w-2xl text-sm text-[#52514e]">
          <strong className="text-[#0b0b0b]">Held-out TEST-set performance</strong> -- the final,
          once-only evaluation split the model never saw during training or threshold tuning (see
          the Day 5 audit). This is different from validation numbers shown elsewhere during
          development, and different again from the live/simulated traffic on the Dashboard and
          Fraud Spike pages.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Model version" value={data.model_version} caption={data.model_name} />
        <StatCard label="Training date" value={formatTimestamp(data.training_date)} />
        <StatCard label="Dataset" value={data.dataset_version} compact />
        <StatCard label="Classification threshold" value={data.threshold.toFixed(2)} />
      </div>

      <div className="rounded-lg border border-[#e1e0d9] bg-[#fcfcfb] p-6">
        <h2 className="text-base font-semibold text-[#0b0b0b]">Test-set metrics</h2>
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

      <div className="rounded-lg border border-[#e1e0d9] bg-[#fcfcfb] p-6">
        <h2 className="text-base font-semibold text-[#0b0b0b]">Confusion matrix</h2>
        <p className="mt-1 text-xs text-[#898781]">
          {data.test_set_size.toLocaleString()} held-out test transactions, at threshold {data.threshold.toFixed(2)}.
        </p>
        <div className="mt-4">
          <ConfusionMatrix tp={data.tp} fp={data.fp} fn={data.fn} tn={data.tn} />
        </div>
      </div>

      <div className="rounded-lg border border-[#e1e0d9] bg-[#fcfcfb] p-4 text-sm text-[#52514e]">
        <strong className="text-[#0b0b0b]">A note on what's real vs. simulated:</strong> this page's
        numbers come from the actual, audited held-out test set -- real historical transactions,
        scored once, never touched for tuning. The <strong className="text-[#0b0b0b]">Dashboard</strong>,{' '}
        <strong className="text-[#0b0b0b]">High-Risk Transactions</strong>, and{' '}
        <strong className="text-[#0b0b0b]">Fraud Spike</strong> pages instead show predictions made
        during this demo session -- either replayed real transactions from{' '}
        <code className="rounded bg-[#f0efec] px-1 py-0.5 text-xs">simulator/simulate.py</code> or
        manual API calls. Both are genuine model outputs on real transaction data; neither is
        fabricated. But they answer different questions -- this page answers "how good is the
        model," the others answer "what is happening right now" -- and the two should never be
        quoted interchangeably.
      </div>
    </div>
  );
}
