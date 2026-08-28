import { DriftStatusBadge } from './Badge';
import { DRIFT_STATUS_LEVEL, getLevelColor } from '../theme/colors';
import { useThemeMode } from '../theme/ThemeProvider';
import type { DriftReportOut, FeatureDriftOut } from '../types/api';

/** Display-only cap on the bar width -- PSI itself has no fixed upper
 * bound (see src/monitoring/drift_detector.py), so a feature with a very
 * large score (this app has genuinely seen hour_of_day PSI > 5, see that
 * module's docstring for why) still renders as a full bar rather than
 * stretching the layout or needing a log scale for a lower-priority page
 * section. The exact PSI number is always shown alongside it regardless.
 */
const PSI_BAR_CAP = 0.5;

const FEATURE_LABEL: Record<string, string> = {
  Amount: 'Amount',
  amount_zscore: 'Amount z-score',
  hour_of_day: 'Hour of day',
  fraud_probability: 'Fraud probability',
};

function DriftFeatureRow({ feature, color }: { feature: FeatureDriftOut; color: string }) {
  const widthPercent = Math.min(100, (feature.psi / PSI_BAR_CAP) * 100);
  return (
    <div className="flex items-center gap-3">
      <div className="w-36 shrink-0 text-sm text-text-primary">{FEATURE_LABEL[feature.feature] ?? feature.feature}</div>
      <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-bg-surface-raised">
        <div
          className="absolute top-0 left-0 h-full rounded-full transition-[width] duration-300 ease-out"
          style={{ width: `${widthPercent}%`, backgroundColor: color }}
        />
      </div>
      <div className="w-16 shrink-0 text-right font-mono text-xs tabular-nums" style={{ color }}>
        {feature.psi.toFixed(3)}
      </div>
    </div>
  );
}

/** Tier 3B: training-vs-live feature drift, as a section on Model
 * Performance rather than its own nav page -- a lower-priority,
 * illustrative capability shouldn't claim equal nav real estate next to
 * the seven top-level pages this product is actually built around. PSI
 * method, thresholds, and every honesty caveat live in
 * src/monitoring/drift_detector.py -- this component only renders what
 * that report already decided. */
export function DriftMonitor({ report }: { report: DriftReportOut }) {
  const mode = useThemeMode();

  return (
    <div className="space-y-6 border-t border-border pt-8">
      <div>
        <h1 className="font-display text-lg font-semibold text-text-primary">Model Drift Monitoring (Tier 3B)</h1>
        <p className="mt-1 max-w-2xl text-sm text-text-secondary">
          Compares the fraud model&apos;s TRAINING feature distribution against the last{' '}
          {report.live_sample_size.toLocaleString()} live-scored predictions, using the{' '}
          <a
            href="https://en.wikipedia.org/wiki/Population_stability_index"
            target="_blank"
            rel="noreferrer"
            className="text-text-primary underline underline-offset-2 hover:text-accent"
          >
            Population Stability Index
          </a>{' '}
          (PSI) -- see below for what that measures.
        </p>
      </div>

      {/* A standing disclosure, not a live alert -- deliberately NOT the
          reserved accent colors. Weight (thicker border) carries the
          emphasis instead. */}
      <div className="rounded-xl border-2 border-text-primary bg-bg-surface-raised p-4 text-sm text-text-primary">
        <strong>Read this before trusting these numbers:</strong> with demo/simulator-scale traffic,
        &ldquo;recent live-scored predictions&rdquo; means dozens to a few hundred rows -- nowhere near
        what a real deployment would compare against. This section is illustrative of the capability
        (the plumbing from training baseline to live comparison to this badge genuinely works), not a
        production-grade drift signal. PSI thresholds below are a standard, widely-used convention,
        not tuned against this project&apos;s own data.
      </div>

      {report.insufficient_data ? (
        <div className="card p-6 text-sm text-text-secondary">
          Not enough live-scored traffic yet to compare distributions ({report.live_sample_size} of a
          minimum {report.min_live_sample_size} predictions needed). Score some transactions
          (Dashboard, or{' '}
          <code className="rounded bg-bg-surface-raised px-1 py-0.5 text-xs">simulator/simulate.py</code>) and
          refresh this page.
        </div>
      ) : (
        <div className="card p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="font-display text-base font-semibold text-text-primary">Per-feature drift (PSI)</h2>
            <DriftStatusBadge status={report.overall_status} />
          </div>
          <p className="mt-1 text-xs text-text-muted">
            Baseline: {report.features[0]?.reference_sample_size.toLocaleString() ?? '—'} training rows. Live
            window: last {report.live_sample_size.toLocaleString()} scored predictions. PSI &lt; 0.10 stable,
            0.10-0.25 moderate, &gt;= 0.25 significant.
          </p>
          <div className="mt-5 space-y-3">
            {report.features.map((feature) => (
              <DriftFeatureRow key={feature.feature} feature={feature} color={getLevelColor(mode, DRIFT_STATUS_LEVEL[feature.status])} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
