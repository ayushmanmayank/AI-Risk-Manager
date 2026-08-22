interface StatCardProps {
  label: string;
  value: string;
  caption?: string;
  /** Use for a value that's a longer string (e.g. a dataset name) rather
   * than a short number/percent -- the default text-2xl is sized for the
   * latter and wraps awkwardly for longer text. */
  compact?: boolean;
}

/** Stat tile: label (sentence case) + value (semibold), per dataviz skill's figure contract. */
export function StatCard({ label, value, caption, compact = false }: StatCardProps) {
  return (
    <div className="rounded-lg border border-[#e1e0d9] bg-[#fcfcfb] p-4 shadow-sm">
      <div className="text-sm text-[#52514e]">{label}</div>
      <div className={`mt-1 font-semibold text-[#0b0b0b] ${compact ? 'text-base' : 'text-2xl'}`}>{value}</div>
      {caption && <div className="mt-1 text-xs text-[#898781]">{caption}</div>}
    </div>
  );
}
