import { useNavigate } from 'react-router-dom';
import { getChargebacks } from '../api/client';
import { useApiData } from '../api/hooks';
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/AsyncState';
import { FlaggedInAdvanceBadge, RiskTierBadge } from '../components/Badge';
import type { ChargebackListItemOut } from '../types/api';
import { formatAmount, formatTimestamp } from '../utils/format';

export function ChargebackCenter() {
  const navigate = useNavigate();
  const chargebacks = useApiData<ChargebackListItemOut[]>(getChargebacks);

  if (chargebacks.status === 'loading') return <LoadingBlock />;
  if (chargebacks.status === 'error') {
    return <ErrorBlock message={chargebacks.error.message} onRetry={chargebacks.refetch} />;
  }

  const data = chargebacks.data;

  return (
    <div className="space-y-6">
      <div className="card-dark p-6">
        <h1 className="font-display text-lg font-semibold text-text-primary">Chargeback Evidence Center</h1>
        <p className="mt-1 max-w-2xl text-sm text-text-secondary">
          <strong className="text-text-primary">Chargeback and refund records here are seeded/simulated
          demo data</strong> -- this project has no real chargeback history. The transaction and
          risk-prediction data each one is layered onto is real (from{' '}
          <code className="rounded bg-bg-surface-raised px-1 py-0.5 text-xs">simulator/simulate.py</code> replays
          or manual API calls), never fabricated.
        </p>
      </div>

      {data.length === 0 ? (
        <EmptyBlock
          title="No chargebacks yet"
          description="Run src/evidence/seed_chargebacks.py to seed a handful of simulated chargebacks against real scored transactions."
        />
      ) : (
        <div className="overflow-x-auto card-dense-dark">
          <table className="min-w-full divide-y divide-border text-sm">
            <thead>
              <tr className="text-left text-xs font-medium tracking-wide text-text-muted uppercase">
                <th className="px-4 py-3">Chargeback ID</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Reason</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Risk tier at scoring</th>
                <th className="px-4 py-3">Flagged in advance?</th>
                <th className="px-4 py-3">Filed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {data.map((item) => (
                <tr
                  key={item.chargeback_id}
                  onClick={() => navigate(`/chargebacks/${item.chargeback_id}`)}
                  className="cursor-pointer hover:bg-bg-surface-raised"
                >
                  <td className="max-w-[180px] truncate px-4 py-3 font-mono text-xs text-text-secondary">
                    {item.chargeback_id}
                  </td>
                  <td className="px-4 py-3 font-mono tabular-nums text-text-primary">{formatAmount(item.amount)}</td>
                  <td className="px-4 py-3 text-text-primary">{item.reason}</td>
                  <td className="px-4 py-3 text-text-secondary">{item.status}</td>
                  <td className="px-4 py-3">
                    {item.risk_tier_at_scoring ? (
                      <RiskTierBadge tier={item.risk_tier_at_scoring} onDark />
                    ) : (
                      <span className="text-xs text-text-muted">no data</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <FlaggedInAdvanceBadge
                      flagged={item.was_flagged_in_advance}
                      hasData={item.risk_tier_at_scoring !== null}
                      onDark
                    />
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-text-secondary">{formatTimestamp(item.timestamp)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
