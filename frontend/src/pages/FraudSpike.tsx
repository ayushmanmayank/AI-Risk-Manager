import { getAlerts } from '../api/client';
import { usePolling } from '../api/hooks';
import { ErrorBlock, LoadingBlock } from '../components/AsyncState';
import { SeverityBadge } from '../components/Badge';
import { FraudRateComparisonChart } from '../components/FraudRateComparisonChart';
import { StatCard } from '../components/StatCard';
import { SEVERITY_COLOR } from '../theme/colors';
import type { AlertsStatusOut } from '../types/api';
import { formatChangePercent, formatTimestamp } from '../utils/format';

// Auto-poll so the page reflects a spike within a few seconds of it
// actually happening, without the presenter needing to click anything
// during a live demo -- this page's whole purpose is "is something wrong
// right now," which a one-time fetch can't answer. 3s balances feeling
// live against hammering the backend; a manual Refresh button is also
// provided for a presenter who wants to force an immediate check.
const POLL_INTERVAL_MS = 3000;

function formatRate(value: number): string {
  return `${(value * 100).toFixed(3)}%`;
}

export function FraudSpike() {
  const poll = usePolling<AlertsStatusOut>(getAlerts, POLL_INTERVAL_MS);

  if (poll.status === 'loading') return <LoadingBlock />;
  if (poll.status === 'error') {
    return <ErrorBlock message={poll.error.message} onRetry={poll.refetch} />;
  }

  const data = poll.data;
  const isCalm = !data.is_spike_active;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-lg font-semibold text-text-primary">Fraud Spike Detector</h1>
          <p className="mt-1 max-w-2xl text-sm text-text-secondary">
            Live view of the rolling fraud-rate anomaly detector: compares the HIGH-risk rate among
            the last {data.window_size || 'N'} scored transactions against the model's baseline
            HIGH-tier rate from training data. Auto-refreshes every {POLL_INTERVAL_MS / 1000}s.
          </p>
          {poll.isStale && (
            <p className="mt-1 text-xs text-risk-high">Last refresh failed -- showing the previous reading.</p>
          )}
        </div>
        <button
          onClick={poll.refetch}
          className="shrink-0 rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-bg-surface-raised focus-visible:outline-2 focus-visible:outline-[var(--color-accent)] focus-visible:outline-offset-2"
        >
          Refresh now
        </button>
      </div>

      {/* Calm / active-spike status banner -- the dominant element on the
          page. transition-colors gives the ONE deliberate motion moment on
          this page: a brief crossfade when the state actually changes, not
          a continuous pulse -- see the redesign's motion plan. */}
      <div
        className="rounded-lg border-2 p-6 transition-colors duration-200"
        style={{
          borderColor: SEVERITY_COLOR[data.severity],
          backgroundColor: `${SEVERITY_COLOR[data.severity]}1a`,
        }}
      >
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xl font-semibold" style={{ color: SEVERITY_COLOR[data.severity] }}>
              {isCalm ? 'No active spike' : 'Active fraud-rate spike detected'}
            </p>
            <p className="mt-1 text-sm text-text-secondary">
              {isCalm
                ? "Recent traffic's HIGH-risk rate is within normal range."
                : `First detected ${data.first_detected_at ? formatTimestamp(data.first_detected_at) : 'just now'}.`}
            </p>
            {data.insufficient_data && (
              <p className="mt-1 text-xs text-text-muted">
                Only {data.window_size} prediction{data.window_size === 1 ? '' : 's'} scored so far --
                not enough history yet for a confident read (needs at least 10).
              </p>
            )}
          </div>
          <SeverityBadge severity={data.severity} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Current fraud rate"
          value={formatRate(data.current_fraud_rate)}
          caption={`last ${data.window_size} predictions`}
        />
        <StatCard
          label="Baseline fraud rate"
          value={formatRate(data.baseline_fraud_rate)}
          caption="training-set HIGH-tier rate"
        />
        <StatCard label="Change vs. baseline" value={formatChangePercent(data.current_fraud_rate, data.baseline_fraud_rate)} />
        <StatCard label="Anomaly score (z)" value={data.anomaly_score.toFixed(2)} caption="spike threshold: z >= 3.0" />
      </div>

      <div className="rounded-lg border border-border bg-bg-surface p-6">
        <h2 className="font-display text-base font-semibold text-text-primary">Current vs. baseline fraud rate</h2>
        <FraudRateComparisonChart
          currentRate={data.current_fraud_rate}
          baselineRate={data.baseline_fraud_rate}
          severity={data.severity}
        />
      </div>

      <div className="rounded-lg border border-border bg-bg-surface p-6">
        <h2 className="font-display text-base font-semibold text-text-primary">Alert history</h2>
        {data.recent_alerts.length === 0 ? (
          <p className="mt-3 text-sm text-text-secondary">No spike alerts have been triggered yet.</p>
        ) : (
          <ul className="mt-3 divide-y divide-border">
            {data.recent_alerts.map((alert) => (
              <li key={alert.alert_id} className="flex flex-wrap items-start justify-between gap-4 py-3 text-sm">
                <div>
                  <SeverityBadge severity={alert.severity} />
                  <p className="mt-1 text-text-primary">{alert.description}</p>
                </div>
                <span className="shrink-0 font-mono text-xs text-text-muted">{formatTimestamp(alert.created_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
