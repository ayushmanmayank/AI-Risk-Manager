import { useEffect, useState } from 'react';
import { simulate } from '../api/client';
import { useLiveApiData } from '../api/hooks';
import { ErrorBlock, LoadingBlock } from '../components/AsyncState';
import { PrecisionRecallCurveChart } from '../components/PrecisionRecallCurveChart';
import type { CurvePoint } from '../components/PrecisionRecallCurveChart';
import { StatCard } from '../components/StatCard';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import { formatAmount } from '../utils/format';

// 150ms: the backend responds in single-digit milliseconds (see
// api/services/simulation_service.py's precomputed validation-set
// probabilities), so this isn't about backend load -- it's purely to
// avoid firing a request on every pixel of a fast slider drag, which
// would otherwise queue up dozens of in-flight requests per second.
const DEBOUNCE_MS = 150;

// The curve is fetched once on mount (not on every slider move): 51
// points at 0.02 steps across the full 0-1 range, each a normal
// /simulate call run in parallel. At a few ms server-side each, 51 in
// parallel is still well under a second total.
const CURVE_THRESHOLDS = Array.from({ length: 51 }, (_, i) => Math.round(i * 2) / 100);

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function ThresholdSimulator() {
  const [threshold, setThreshold] = useState(0.5);
  const [retryNonce, setRetryNonce] = useState(0);
  const debouncedThreshold = useDebouncedValue(threshold, DEBOUNCE_MS);

  const live = useLiveApiData(() => simulate({ threshold: debouncedThreshold }), [debouncedThreshold, retryNonce]);

  const [curve, setCurve] = useState<CurvePoint[] | null>(null);
  const [curveError, setCurveError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all(CURVE_THRESHOLDS.map((t) => simulate({ threshold: t })))
      .then((results) => {
        if (cancelled) return;
        setCurve(results.map((r) => ({ threshold: r.threshold, precision: r.precision, recall: r.recall })));
      })
      .catch((error: unknown) => {
        if (!cancelled) setCurveError(error instanceof Error ? error.message : String(error));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (live.status === 'loading') return <LoadingBlock />;
  if (live.status === 'error') {
    return <ErrorBlock message={live.error.message} onRetry={() => setRetryNonce((n) => n + 1)} />;
  }

  const data = live.data;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-lg font-semibold text-[#0b0b0b]">Threshold Simulator</h1>
        <p className="mt-1 max-w-2xl text-sm text-[#52514e]">
          Shows what would happen at any decision threshold, computed against the{' '}
          <strong className="text-[#0b0b0b]">validation set's</strong> pre-scored predictions
          (Day 1/2's held-out validation split) -- <strong className="text-[#0b0b0b]">not live
          traffic</strong>. Move the slider to see the tradeoff.
        </p>
      </div>

      <div className="rounded-lg border border-[#e1e0d9] bg-[#fcfcfb] p-4 text-sm text-[#52514e]">
        <strong className="text-[#0b0b0b]">The core tradeoff:</strong> a{' '}
        <strong className="text-[#0b0b0b]">lower</strong> threshold catches more fraud but flags
        more legitimate transactions too (more customer friction / false positives). A{' '}
        <strong className="text-[#0b0b0b]">higher</strong> threshold reduces that friction but
        misses more fraud. No threshold improves both at once -- the slider below trades one for
        the other.
      </div>

      <div className="rounded-lg border border-[#e1e0d9] bg-[#fcfcfb] p-6">
        <div className="flex items-center justify-between">
          <label htmlFor="threshold-slider" className="text-sm font-medium text-[#0b0b0b]">
            Risk threshold
          </label>
          <span className="text-2xl font-semibold text-[#0b0b0b]">{threshold.toFixed(2)}</span>
        </div>
        <input
          id="threshold-slider"
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={threshold}
          onChange={(event) => setThreshold(Number(event.target.value))}
          className="mt-3 w-full accent-[#2a78d6]"
        />
        <div className="mt-1 flex justify-between text-xs text-[#898781]">
          <span>0.00 -- flag everything</span>
          <span>1.00 -- flag almost nothing</span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard label="Precision" value={formatPercent(data.precision)} caption="of flagged, % actually fraud" />
        <StatCard label="Recall" value={formatPercent(data.recall)} caption="of actual fraud, % caught" />
        <StatCard
          label="False positive rate"
          value={formatPercent(data.false_positive_rate)}
          caption="of legitimate txns, % wrongly flagged"
        />
        <StatCard
          label="Fraud caught"
          value={`${data.fraud_caught_count} / ${data.fraud_caught_count + data.fn}`}
          caption={formatPercent(data.fraud_caught_percent / 100)}
        />
        <StatCard
          label="Transactions affected"
          value={data.transactions_affected_count.toLocaleString()}
          caption={`${data.transactions_affected_percent.toFixed(2)}% of validation set (REVIEW/HOLD)`}
        />
        <StatCard
          label="Expected financial loss"
          value={formatAmount(data.expected_financial_loss)}
          caption={`fp_cost=${data.false_positive_cost}, fn_cost=${data.false_negative_cost} (placeholder units)`}
        />
      </div>

      <div className="rounded-lg border border-[#e1e0d9] bg-[#fcfcfb] p-6">
        <h2 className="text-base font-semibold text-[#0b0b0b]">Precision / recall vs. threshold</h2>
        <p className="mt-1 text-xs text-[#898781]">Dashed line marks the current slider position.</p>
        {curveError ? (
          <p className="mt-3 text-sm text-[#d03b3b]">Couldn't load the curve: {curveError}</p>
        ) : curve ? (
          <PrecisionRecallCurveChart points={curve} currentThreshold={debouncedThreshold} />
        ) : (
          <div className="mt-3 h-[280px] animate-pulse rounded-lg bg-[#f0efec]" />
        )}
      </div>
    </div>
  );
}
