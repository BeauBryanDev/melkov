interface GoldenSpinnerProps {
  /** Outer diameter in px. */
  size?: number;
  className?: string;
}

/**
 * A gilded rotating ring, shown while Melkov is thinking or answering.
 *
 * Two rings turning against each other: an outer gold arc sweeping clockwise
 * and an inner, dimmer one counter-clockwise, which reads as a slow gilded
 * orbit rather than the usual utility spinner — in keeping with the
 * Baroque/Rococo palette rather than the portfolio's HUD look.
 *
 * Purely decorative: `AnalysisStatus` already carries `role="status"` and the
 * typing indicator carries the label, so this is hidden from assistive tech to
 * avoid announcing the same wait three times. The global
 * `prefers-reduced-motion` rule in `styles.css` stops the rotation and leaves
 * a static gold ring.
 */
export function GoldenSpinner({ size = 26, className }: GoldenSpinnerProps) {
  return (
    <span
      aria-hidden="true"
      className={className ? `golden-spinner ${className}` : "golden-spinner"}
      style={{ width: size, height: size }}
    >
      <span className="golden-spinner-ring" />
      <span className="golden-spinner-ring golden-spinner-ring-inner" />
      <span className="golden-spinner-core" />
    </span>
  );
}
