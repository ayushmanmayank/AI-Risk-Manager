import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getTransactions } from '../api/client';
import { useApiData } from '../api/hooks';
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/AsyncState';
import { DecisionBadge, RiskTierBadge } from '../components/Badge';
import { RiskMeter } from '../components/RiskMeter';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import type { Decision, PaginatedTransactions, RiskTier } from '../types/api';
import { formatAmount, formatTimestamp } from '../utils/format';

const RISK_TIER_OPTIONS: Array<RiskTier | 'ALL'> = ['ALL', 'LOW', 'MEDIUM', 'HIGH'];
const DECISION_OPTIONS: Array<Decision | 'ALL'> = ['ALL', 'ALLOW', 'REVIEW', 'HOLD'];

// Client-side filtering is fine at hackathon-scale data volume; move to
// server-side query params if the predictions table grows meaningfully.
const FETCH_LIMIT = 200;

export function HighRiskTransactions() {
  const navigate = useNavigate();
  const transactions = useApiData<PaginatedTransactions>(() => getTransactions({ limit: FETCH_LIMIT }));
  const [tierFilter, setTierFilter] = useState<RiskTier | 'ALL'>('ALL');
  const [decisionFilter, setDecisionFilter] = useState<Decision | 'ALL'>('ALL');

  const filtered = useMemo(() => {
    if (transactions.status !== 'success') return [];
    return transactions.data.items.filter(
      (item) =>
        (tierFilter === 'ALL' || item.risk_tier === tierFilter) &&
        (decisionFilter === 'ALL' || item.decision === decisionFilter),
    );
  }, [transactions, tierFilter, decisionFilter]);

  if (transactions.status === 'loading') return <LoadingBlock />;

  if (transactions.status === 'error') {
    return <ErrorBlock message={transactions.error.message} onRetry={transactions.refetch} />;
  }

  if (transactions.data.items.length === 0) {
    return (
      <EmptyBlock
        title="No predictions yet"
        description="Once transactions are scored via POST /api/v1/predict, they'll show up here."
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-4">
        <FilterSelect label="Risk tier" value={tierFilter} options={RISK_TIER_OPTIONS} onChange={setTierFilter} />
        <FilterSelect label="Decision" value={decisionFilter} options={DECISION_OPTIONS} onChange={setDecisionFilter} />
      </div>

      <div className="overflow-x-auto card-dense">
        <table className="min-w-full divide-y divide-border text-sm">
          <thead>
            <tr className="text-left text-xs font-medium tracking-wide text-text-muted uppercase">
              <th className="px-4 py-3">Transaction ID</th>
              <th className="px-4 py-3">Amount</th>
              <th className="px-4 py-3">Fraud probability</th>
              <th className="px-4 py-3">Risk tier</th>
              <th className="px-4 py-3">Expected loss</th>
              <th className="px-4 py-3">Decision</th>
              <th className="px-4 py-3">Timestamp</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {filtered.map((item) => (
              <tr key={item.transaction_id} onClick={() => navigate(`/transactions/${item.transaction_id}`)} className="row-glow">
                <td className="max-w-[220px] truncate px-4 py-3 font-mono text-xs text-text-secondary">{item.transaction_id}</td>
                <td className="px-4 py-3 font-mono tabular-nums text-text-primary">{formatAmount(item.amount)}</td>
                <td className="px-4 py-3">
                  <RiskMeter probability={item.fraud_probability} tier={item.risk_tier} compact />
                </td>
                <td className="px-4 py-3">
                  <RiskTierBadge tier={item.risk_tier} />
                </td>
                <td className="px-4 py-3 font-mono tabular-nums text-text-primary">{formatAmount(item.expected_loss)}</td>
                <td className="px-4 py-3">
                  <DecisionBadge decision={item.decision} />
                </td>
                <td className="px-4 py-3 font-mono text-xs text-text-secondary">{formatTimestamp(item.timestamp)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <p className="px-4 py-6 text-center text-sm text-text-secondary">No transactions match the selected filters.</p>
        )}
      </div>
    </div>
  );
}

function FilterSelect<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: T[];
  onChange: (value: T) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-sm text-text-secondary">
      {label}
      <Select value={value} onValueChange={(next) => onChange(next as T)}>
        <SelectTrigger className="min-w-24">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((option) => (
            <SelectItem key={option} value={option}>
              {option}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </label>
  );
}
