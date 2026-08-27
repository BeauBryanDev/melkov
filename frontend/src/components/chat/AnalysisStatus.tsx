import type { ChatStatus } from "../../types/chat";
import { TypingIndicator } from "./TypingIndicator";
import { ChatPrinceAvatar } from "./ChatPrinceAvatar";
import { GoldenSpinner } from "../ui/GoldenSpinner";
import { useThinkingCue } from "./useThinkingCue";

interface AnalysisStatusProps {
  status: ChatStatus;
}

/**
 * What Melkov is doing while the visitor waits.
 *
 * FRONTEND_SPEC §19 forbids faked progress, and `POST /chat` returns only
 * once the whole turn is done. So nothing here is a progress bar: the
 * elapsed count is measured, and the rest is motion — a shimmer across the
 * bubble and the typing dots — that says "still working", not "nearly there".
 */
export function AnalysisStatus({ status }: AnalysisStatusProps) {
  const examining = status === "analyzing";
  const { phrase, seconds } = useThinkingCue(examining);

  return (
    <article
      aria-live="polite"
      className="chat-message chat-message-melkov chat-message-pending"
      role="status"
    >
      <div className="chat-header">
        <div className="chat-role">
          <ChatPrinceAvatar size={34} />
          <span>Melkov</span>
        </div>
        {seconds >= 3 ? <span className="chat-pending-clock">{seconds}s</span> : null}
      </div>
      <div className="chat-pending-line">
        <GoldenSpinner />
        <p className="chat-pending-copy" key={phrase}>
          {phrase}
        </p>
        <TypingIndicator />
      </div>
      {examining ? (
        <p className="chat-pending-note">
          Reading the canvas can take a moment while the atelier warms up.
        </p>
      ) : null}
    </article>
  );
}
