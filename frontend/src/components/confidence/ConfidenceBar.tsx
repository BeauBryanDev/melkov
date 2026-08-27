import { formatScore } from "../../utils/format";

interface ConfidenceBarProps {
  label: string;
  /** A value between 0 and 1. */
  score: number;
  /** The highest-scoring classification, which carries the gold glow. */
  primary?: boolean;
}

/** One row of the classification chart. */
export function ConfidenceBar({ label, score, primary = false }: ConfidenceBarProps) {
  const percent = Math.max(0, Math.min(1, score)) * 100;

  return (
    <div className={`confidence-row${primary ? " confidence-row-primary" : ""}`}>
      <span className="confidence-label">{label}</span>
      <div
        aria-label={`${label} ${formatScore(score)}`}
        aria-valuemax={100}
        aria-valuemin={0}
        aria-valuenow={Math.round(percent)}
        className="confidence-track"
        role="meter"
      >
        <div className="confidence-bar" style={{ width: `${percent}%` }} />
      </div>
      <span className="confidence-value">{formatScore(score)}</span>
    </div>
  );
}
