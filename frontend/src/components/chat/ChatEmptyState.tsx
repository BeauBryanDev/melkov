import { ChatPrinceAvatar } from "./ChatPrinceAvatar";

interface ChatEmptyStateProps {
  hasArtwork: boolean;
}

/**
 * What the chat shows before a word has been exchanged.
 *
 * This replaces the three hardcoded demonstration bubbles the panel used to
 * open with (FRONTEND_SPEC §13): an introduction the visitor can see is an
 * introduction, rather than a scripted conversation posing as a real one.
 */
export function ChatEmptyState({ hasArtwork }: ChatEmptyStateProps) {
  return (
    <div className="chat-empty">
      <ChatPrinceAvatar size={72} />
      <p className="chat-empty-name">Melkov</p>
      <p className="chat-empty-role">AI Art Expert</p>
      <p className="chat-empty-copy">
        {hasArtwork
          ? "The work is in the frame. Ask about its style, technique, period, or the history behind it."
          : "Hang a painting in the frame, or ask Melkov to paint one, and begin a conversation about its style, technique, period, and historical context."}
      </p>
    </div>
  );
}
