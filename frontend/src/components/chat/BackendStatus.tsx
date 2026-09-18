import { useBackendHealth } from "../../hooks/useBackendHealth";

const LABEL: Record<string, string> = {
  checking: "Checking",
  online: "Online",
  offline: "Offline",
};

const TITLE: Record<string, string> = {
  checking: "Asking Melkov's atelier whether it is open…",
  online: "Melkov is at his easel and answering.",
  offline: "The atelier is closed — Melkov cannot be reached right now.",
};

/**
 * Whether Melkov himself is reachable, shown beside the chat title.
 *
 * The site is a static bundle on Vercel; Melkov lives on a separate server
 * that is sometimes stopped. The page therefore loads beautifully whether or
 * not there is anyone home, and a visitor arriving at midnight would otherwise
 * learn that only by writing a question and watching it fail. This says so
 * before they type a word.
 *
 * Rendered as a live region so the change is announced rather than only seen —
 * the colour of the dot is the fastest signal for most visitors and no signal
 * at all for some, which is why the word sits next to it and is not decoration
 * to be dropped at narrow widths.
 */
export function BackendStatus() {
  const health = useBackendHealth();

  return (
    <span
      aria-live="polite"
      className="backend-status"
      data-state={health}
      role="status"
      title={TITLE[health]}
    >
      <span aria-hidden="true" className="backend-status-dot" />
      <span className="backend-status-label">{LABEL[health]}</span>
    </span>
  );
}
