import { useEffect, useState } from "react";

/** How long the reveal takes, whatever the reply's length. */
const REVEAL_MS = 1800;
/** Frame interval; ~30 fps is smooth enough for text and cheap on re-renders. */
const STEP_MS = 32;
/** A reply older than this at mount is history, not an answer arriving now. */
const FRESH_MS = 4000;

interface RevealedText {
  text: string;
  revealing: boolean;
}

/**
 * Melkov "typing out" a reply that has, in truth, already arrived whole.
 * 
 * POST /chat returns once, so there is nothing to stream; this is a short,
 * fixed-duration reveal of the finished text, word by word, so the answer
 * reads as being written rather than dropped on the page. It runs only for a
 * message that was added moments ago — a transcript restored from storage on
 * reload shows at once, as does anything the visitor scrolls back to.
 *
 * @param content The full reply text.
 * @param timestamp When the message was added; decides whether to animate.
 */
export function useRevealedText(content: string, 
                                timestamp: string): RevealedText {
  // Decided once, at mount: a message does not become "fresh" again on re-render.
  const [animate] = useState(() => Date.now() - Date.parse(timestamp) < FRESH_MS);
  const [shown, setShown] = useState(animate ? 0 : content.length);

  useEffect(() => {
    if (!animate) {
      return;
    }
    const words = content.split(/(\s+)/);
    const started = Date.now();
    const timer = window.setInterval(() => {
      const progress = Math.min(1, (Date.now() - started) / REVEAL_MS);
      const count = Math.ceil(words.length * progress);
      setShown(words.slice(0, count).join("").length);
      if (progress >= 1) {
        window.clearInterval(timer);
      }
    }, STEP_MS);
    return () => window.clearInterval(timer);
  }, [animate, content]);

  const revealing = shown < content.length;
  return { text: revealing ? content.slice(0, shown) : content, revealing };
}
