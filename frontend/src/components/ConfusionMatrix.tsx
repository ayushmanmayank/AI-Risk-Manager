import { SEVERITY_COLOR } from '../theme/colors';

interface ConfusionMatrixProps {
  tp: number;
  fp: number;
  fn: number;
  tn: number;
}

function Cell({ value, label, color }: { value: number; label: string; color: string }) {
  return (
    <div className="rounded-md border p-4 text-center" style={{ borderColor: color, backgroundColor: `${color}0d` }}>
      <div className="text-lg font-semibold text-[#0b0b0b]">{value.toLocaleString()}</div>
      <div className="text-xs text-[#52514e]">{label}</div>
    </div>
  );
}

/** Simple 2x2 confusion matrix. Correct predictions (TN, TP) use the
 * calm/good color; wrong predictions are split by severity, matching this
 * project's own established cost asymmetry (src/risk/cost_engine.py: a
 * missed fraud costs ~20x a false alarm) -- False Negative gets the more
 * severe color than False Positive, not an arbitrary choice.
 */
export function ConfusionMatrix({ tp, fp, fn, tn }: ConfusionMatrixProps) {
  return (
    <div className="inline-grid grid-cols-[auto_1fr_1fr] gap-2 text-sm">
      <div />
      <div className="px-2 py-1 text-center text-xs font-medium text-[#898781]">Predicted: Legit</div>
      <div className="px-2 py-1 text-center text-xs font-medium text-[#898781]">Predicted: Fraud</div>

      <div className="flex items-center px-2 text-xs font-medium text-[#898781]">Actual: Legit</div>
      <Cell value={tn} label="True Negative" color={SEVERITY_COLOR.NONE} />
      <Cell value={fp} label="False Positive" color={SEVERITY_COLOR.LOW} />

      <div className="flex items-center px-2 text-xs font-medium text-[#898781]">Actual: Fraud</div>
      <Cell value={fn} label="False Negative" color={SEVERITY_COLOR.HIGH} />
      <Cell value={tp} label="True Positive" color={SEVERITY_COLOR.NONE} />
    </div>
  );
}
