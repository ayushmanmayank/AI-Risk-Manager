interface StatCardProps {
  label: string;
  value: string;
  caption?: string;
  /** Use for a value that's a longer string (e.g. a dataset name) rather
   * than a short number/percent -- the default text-2xl is sized for the
   * latter and wraps awkwardly for longer text. */
  compact?: boolean;
  /** PREVIEW ONLY -- Dashboard's card-dark treatment. Swaps the `card`
   * utility for `card-dark`; text colors are unaffected here since they
   * already go through the text-text-primary/secondary/muted utilities
   * that `card-dark` redefines locally via CSS-cascade. Not yet wired up
   * on any other page. */
  onDark?: boolean;
}

/** Stat tile: label (sentence case) + value (semibold, tabular mono --
 * every value here is a number, an amount, or an id, and this redesign's
 * type system reserves mono specifically for that). */
export function StatCard({ label, value, caption, compact = false, onDark = false }: StatCardProps) {
  return (
    <div className={`${onDark ? 'card-dark' : 'card'} p-4`}>
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
