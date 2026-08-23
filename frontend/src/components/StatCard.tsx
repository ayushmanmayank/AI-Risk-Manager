interface StatCardProps {
  label: string;
  value: string;
  caption?: string;
  /** Use for a value that's a longer string (e.g. a dataset name) rather
   * than a short number/percent -- the default text-2xl is sized for the
   * latter and wraps awkwardly for longer text. */
  compact?: boolean;
}

/** Stat tile: label (sentence case) + value (semibold, tabular mono --
 * every value here is a number, an amount, or an id, and this redesign's
 * type system reserves mono specifically for that). */
export function StatCard({ label, value, caption, compact = false }: StatCardProps) {
  return (
    <div className="rounded-lg border border-border bg-bg-surface p-4">
      <div className="text-sm text-text-secondary">{label}</div>
      <div
        className={`mt-1 font-mono font-semibold text-text-primary tabular-nums break-words ${compact ? 'text-base' : 'text-2xl'}`}
      >
        {value}
      </div>
      {caption && <div className="mt-1 text-xs text-text-muted">{caption}</div>}
    </div>
  );
}
