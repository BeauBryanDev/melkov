/** Render a 0–1 score as a whole percentage. */
export function formatScore(score: number): string {
  return `${Math.round(score * 100)}%`;
}

/** Render an already-percentage value. */
export function formatPercent(value: number): string {
  return `${Math.round(value)}%`;
}

/** Clock time for a message header, e.g. "10:24 AM". */
export function formatTime(value: string | Date): string {
  const date = typeof value === "string" ? new Date(value) : value;
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

export function createId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

/**
 * Turn a confidence score into the wording used beside the primary style.
 *
 * @param score A value between 0 and 1.
 */
export function confidenceBand(score: number): string {
  if (score >= 0.75) return "High confidence";
  if (score >= 0.45) return "Moderate confidence";
  return "Low confidence";
}
