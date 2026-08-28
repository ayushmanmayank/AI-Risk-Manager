interface ConfusionMatrixProps {
  tp: number;
  fp: number;
  fn: number;
  tn: number;
  /** What the positive class is called, e.g. "Fraud" or "Returned". */
  positiveLabel?: string;
  /** What the negative class is called, e.g. "Legit" or "Not returned". */
  negativeLabel?: string;
}

function Cell({ value, label }: { value: number; label: string }) {
  return (
    <div className="rounded-md border border-border bg-bg-surface-raised p-4 text-center">
      <div className="font-mono text-lg font-semibold tabular-nums text-text-primary">{value.toLocaleString()}</div>
      <div className="text-xs text-text-secondary">{label}</div>
    </div>
  );
}

/** Simple 2x2 confusion matrix, reused across models. Deliberately fully
 * neutral -- a confusion matrix is a static audit table, not a live
 * alert, so it doesn't get the reserved accent colors; those are earned
 * by real-time risk/severity readings elsewhere in the app, not by a
 * fixed evaluation table. */
export function ConfusionMatrix({ tp, fp, fn, tn, positiveLabel = 'Fraud', negativeLabel = 'Legit' }: ConfusionMatrixProps) {
  return (
    <div className="inline-grid grid-cols-[auto_1fr_1fr] gap-2 text-sm">
      <div />
      <div className="px-2 py-1 text-center text-xs font-medium text-text-secondary">Predicted: {negativeLabel}</div>
      <div className="px-2 py-1 text-center text-xs font-medium text-text-secondary">Predicted: {positiveLabel}</div>

      <div className="flex items-center px-2 text-xs font-medium text-text-secondary">Actual: {negativeLabel}</div>
      <Cell value={tn} label="True Negative" />
      <Cell value={fp} label="False Positive" />

      <div className="flex items-center px-2 text-xs font-medium text-text-secondary">Actual: {positiveLabel}</div>
      <Cell value={fn} label="False Negative" />
      <Cell value={tp} label="True Positive" />
    </div>
  );
}
