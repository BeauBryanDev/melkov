import type { ChatStatus } from "../../types/chat";
import { FeatherWriting } from "./FeatherWriting";
import { ChatPrinceAvatar } from "./ChatPrinceAvatar";
import { useThinkingCue } from "./useThinkingCue";

interface AnalysisStatusProps {
  status: ChatStatus;
}

/**
 * What Melkov is doing while the visitor waits.

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
        {/* The quill on every turn: a turn that carries the image still ends
            in Melkov writing, and the frame shows its own examining state. */}
        <FeatherWriting />
        <p className="chat-pending-copy" key={phrase}>
          {phrase}
        </p>
      </div>
      {examining ? (
        <p className="chat-pending-note">
          Reading the canvas can take a moment while the atelier warms up.
        </p>
      ) : null}
    </article>
  );
}
