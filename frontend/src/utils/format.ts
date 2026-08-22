export function formatAmount(value: number): string {
  return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function formatPercent(count: number, total: number): string {
  if (total === 0) return '0%';
  return `${((count / total) * 100).toFixed(1)}%`;
}

export function formatProbability(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

export function formatTimestamp(value: string): string {
  return new Date(value).toLocaleString();
}

/** Percent change of `current` vs `baseline`, signed. Guards baseline=0
 * (theoretically possible, never actually 0 in practice for this project's
 * baseline, but a live rate could still be exactly 0).
 */
export function formatChangePercent(current: number, baseline: number): string {
  if (baseline === 0) return current === 0 ? '0%' : 'N/A';
  const change = ((current - baseline) / baseline) * 100;
  const sign = change > 0 ? '+' : '';
  return `${sign}${change.toLocaleString(undefined, { maximumFractionDigits: 0 })}%`;
}
