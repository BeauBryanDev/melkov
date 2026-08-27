import { useEffect, useState } from "react";

/** Phrases cycled while a turn is in flight, slowest path last. */
const EXAMINING = [
  "Examining the artwork…",
  "Reading the brushwork…",
  "Weighing the palette…",
  "Consulting the library…",
] as const;

const CONSIDERING = [
  "Considering your question…",
  "Turning it over…",
  "Consulting the library…",
] as const;

interface ThinkingCue {
  phrase: string;
  seconds: number;
}

/**
 * The honest half of the wait: a real elapsed count and a rotating phrase.
 *
 * The backend reports nothing mid-turn, so nothing here claims progress —
 * the seconds are measured, the phrases only say what kind of work is running.
 */
export function useThinkingCue(examining: boolean): ThinkingCue {
  const phrases = examining ? EXAMINING : CONSIDERING;
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const started = Date.now();
    const timer = window.setInterval(
      () => setSeconds(Math.floor((Date.now() - started) / 1000)),
      1000,
    );
    return () => window.clearInterval(timer);
  }, [examining]);

  return { phrase: phrases[Math.min(Math.floor(seconds / 6), phrases.length - 1)], seconds };
}
