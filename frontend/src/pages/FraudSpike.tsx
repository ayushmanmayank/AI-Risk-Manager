import { useEffect, useRef, useState } from 'react';
import { getAlerts } from '../api/client';
import { usePolling } from '../api/hooks';
import { ErrorBlock, LoadingBlock } from '../components/AsyncState';
import { SeverityBadge } from '../components/Badge';
import { FraudRateComparisonChart } from '../components/FraudRateComparisonChart';
import { Sparkline } from '../components/Sparkline';
import type { SparklinePoint } from '../components/Sparkline';
import { StatCard } from '../components/StatCard';
import { SEVERITY_COLOR, TEXT_SECONDARY_ON_DARK } from '../theme/colors';
import type { AlertsStatusOut } from '../types/api';
import { formatChangePercent, formatTimestamp } from '../utils/format';

// Auto-poll so the page reflects a spike within a few seconds of it
// actually happening, without the presenter needing to click anything
// during a live demo -- this page's whole purpose is "is something wrong
// right now," which a one-time fetch can't answer. 3s balances feeling
// live against hammering the backend; a manual Refresh button is also
// provided for a presenter who wants to force an immediate check.
const POLL_INTERVAL_MS = 3000;

// How many recent poll readings the live sparkline keeps on screen --
// ~1 minute of real history at the 3s interval above. This is purely a
// client-side display buffer of values the page already fetches on its
// existing poll; it adds no new API calls or backend data, it just stops
// discarding each reading the instant a newer one arrives. Resets on
// page reload/navigation (never persisted), same as everything else
// this page shows.
const SPARKLINE_MAX_POINTS = 20;

function formatRate(value: number): string {
  return `${(value * 100).toFixed(3)}%`;
}

export function FraudSpike() {
  const poll = usePolling<AlertsStatusOut>(getAlerts, POLL_INTERVAL_MS);
  const [history, setHistory] = useState<SparklinePoint[]>([]);
  const tickRef = useRef(0);

  // Accumulate each already-fetched poll reading into a short client-side
  // buffer for the live trend sparkline below -- no new request, no new
  // data: just retaining values this page already receives instead of
  // discarding the previous reading every 3s. See SPARKLINE_MAX_POINTS.
  useEffect(() => {
    if (poll.status !== 'success') return;
    tickRef.current += 1;
    setHistory((previous) => [...previous, { tick: tickRef.current, value: poll.data.current_fraud_rate }].slice(-SPARKLINE_MAX_POINTS));
    // Only re-run when a genuinely new reading arrives, not on every
    // render (poll.data is a fresh object each successful fetch).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [poll.status === 'success' ? poll.data : null]);

  if (poll.status === 'loading') return <LoadingBlock />;
  if (poll.status === 'error') {
    return <ErrorBlock message={poll.error.message} onRetry={poll.refetch} />;
  }

  const data = poll.data;
  const isCalm = !data.is_spike_active;

  return (
    <div className="space-y-8">
      {/* Header card -- same off-black/rounded/popped-up/glow treatment
          as every other card, rolled out here from the Submission-page
          preview. LIVE indicator and the stale-refresh notice were
          light-surface raw hex before; both needed on-dark equivalents
          now that this sits on a dark card (see theme/colors.ts). */}
      <div className="card-dark flex flex-wrap items-start justify-between gap-4 p-6">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-display text-lg font-semibold text-text-primary">Fraud Spike Detector</h1>
            {/* Neutral, not accent -- "this is polling" is informational,
                not an alert, so it doesn't get the reserved signal color
                under this direction's rule (the calm/active banner below
                is the only thing on this page allowed to use it). */}
            <span className="inline-flex items-center gap-1.5 text-xs font-medium" style={{ color: TEXT_SECONDARY_ON_DARK }}>
              <span className="h-1.5 w-1.5 animate-pulse rounded-full" style={{ backgroundColor: TEXT_SECONDARY_ON_DARK }} />
              LIVE
            </span>
          </div>
          <p className="mt-1 max-w-2xl text-sm text-text-secondary">
            Live view of the rolling fraud-rate anomaly detector: compares the HIGH-risk rate among
            the last {data.window_size || 'N'} scored transactions against the model's baseline
            HIGH-tier rate from training data. Auto-refreshes every {POLL_INTERVAL_MS / 1000}s.
          </p>
          {poll.isStale && (
            <p className="mt-1 text-xs text-accent-on-dark">Last refresh failed -- showing the previous reading.</p>
          )}
        </div>
        <button
          onClick={poll.refetch}
          className="shrink-0 rounded-(--radius-control) border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-bg-surface-raised focus-visible:outline-2 focus-visible:outline-[var(--color-text-primary-on-dark)] focus-visible:outline-offset-2"
        >
          Refresh now
        </button>
      </div>

      {/* Calm / active-spike status banner -- the dominant element on the
          page. transition-colors gives the ONE deliberate motion moment on
          this page: a brief crossfade when the state actually changes, not
          a continuous pulse -- see the redesign's motion plan. */}
      <div
        className="rounded-(--radius-card) border-2 p-6 transition-colors duration-200"
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

      <div className="card-dark p-6">
        <div className="flex items-baseline justify-between">
          <h2 className="font-display text-base font-semibold text-text-primary">Live fraud rate (this session)</h2>
          <span className="font-mono text-xs text-text-muted">last {history.length} readings</span>
        </div>
        <p className="mt-1 text-xs text-text-muted">
          Built from this page's own polling (see "Auto-refreshes every 3s" above) -- no new data beyond what's
          already fetched above, just kept on screen instead of discarded each tick. Resets on reload.
        </p>
        {/* Neutral trend line -- a sparkline is a visualization, not
            itself an alert; only the banner/badge above signal. On-dark
            secondary text tone, since this card is always dark now. */}
        <div className="mt-3">
          <Sparkline points={history} color={TEXT_SECONDARY_ON_DARK} />
        </div>
      </div>

      <div className="card-dark p-6">
        <h2 className="font-display text-base font-semibold text-text-primary">Current vs. baseline fraud rate</h2>
        <FraudRateComparisonChart
          currentRate={data.current_fraud_rate}
          baselineRate={data.baseline_fraud_rate}
          severity={data.severity}
          onDark
        />
      </div>

      <div className="card-dark p-6">
        <h2 className="font-display text-base font-semibold text-text-primary">Alert history</h2>
        {data.recent_alerts.length === 0 ? (
          <p className="mt-3 text-sm text-text-secondary">No spike alerts have been triggered yet.</p>
        ) : (
          <ul className="mt-3 divide-y divide-border">
            {data.recent_alerts.map((alert) => (
              <li key={alert.alert_id} className="flex flex-wrap items-start justify-between gap-4 py-3 text-sm">
                <div>
                  <SeverityBadge severity={alert.severity} onDark />
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
