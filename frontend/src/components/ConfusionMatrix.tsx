import { SEVERITY_COLOR } from '../theme/colors';

interface ConfusionMatrixProps {
  tp: number;
  fp: number;
  fn: number;
  tn: number;
  /** What the positive class is called, e.g. "Fraud" or "Returned". */
  positiveLabel?: string;
  /** What the negative class is called, e.g. "Legit" or "Not returned". */
  negativeLabel?: string;
  /** Whether a missed positive (FN) is asserted to cost more than a false
   * alarm (FP) -- true only when this project has actually defined that
   * cost asymmetry for the model being shown (see src/risk/cost_engine.py
   * for the fraud model's ~20x figure). Defaults to true for backward
   * compatibility with the fraud model's own usage; any model without an
   * established cost model (e.g. the Tier 2 return-risk scorer) must pass
   * false explicitly rather than silently inheriting a cost claim that
   * was never made for it.
   */
  costAsymmetryEstablished?: boolean;
}

function Cell({ value, label, color }: { value: number; label: string; color: string }) {
  return (
    <div className="rounded-md border p-4 text-center" style={{ borderColor: color, backgroundColor: `${color}0d` }}>
      <div className="text-lg font-semibold text-[#0b0b0b]">{value.toLocaleString()}</div>
      <div className="text-xs text-[#52514e]">{label}</div>
    </div>
  );
}

/** Simple 2x2 confusion matrix, reused across models -- see
 * `positiveLabel`/`negativeLabel`/`costAsymmetryEstablished` above for
 * why those are configurable rather than hardcoded to "Fraud"/"Legit":
 * a different model's positive class, and whether its FN/FP severity
 * ordering has any real justification, must never be silently inherited
 * from whichever model happened to use this component first.
 */
export function ConfusionMatrix({
  tp,
  fp,
  fn,
  tn,
  positiveLabel = 'Fraud',
  negativeLabel = 'Legit',
  costAsymmetryEstablished = true,
}: ConfusionMatrixProps) {
  const fpColor = costAsymmetryEstablished ? SEVERITY_COLOR.LOW : SEVERITY_COLOR.NONE;
  const fnColor = costAsymmetryEstablished ? SEVERITY_COLOR.HIGH : SEVERITY_COLOR.NONE;

  return (
    <div className="inline-grid grid-cols-[auto_1fr_1fr] gap-2 text-sm">
      <div />
      <div className="px-2 py-1 text-center text-xs font-medium text-[#898781]">
        Predicted: {negativeLabel}
      </div>
      <div className="px-2 py-1 text-center text-xs font-medium text-[#898781]">
        Predicted: {positiveLabel}
      </div>

      <div className="flex items-center px-2 text-xs font-medium text-[#898781]">Actual: {negativeLabel}</div>
      <Cell value={tn} label="True Negative" color={SEVERITY_COLOR.NONE} />
      <Cell value={fp} label="False Positive" color={fpColor} />

      <div className="flex items-center px-2 text-xs font-medium text-[#898781]">Actual: {positiveLabel}</div>
      <Cell value={fn} label="False Negative" color={fnColor} />
      <Cell value={tp} label="True Positive" color={SEVERITY_COLOR.NONE} />
    </div>
  );
}
