import { useState } from "react";
import type { ChatMessage as ChatMessageType, ChatStatus } from "../../types/chat";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { ChatEmptyState } from "./ChatEmptyState";
import { AnalysisStatus } from "./AnalysisStatus";
import { Panel } from "../ui/Panel";
import { useAutoScroll } from "../../hooks/useAutoScroll";

interface ChatPanelProps {
  messages: ChatMessageType[];
  status: ChatStatus;
  busy: boolean;
  hasArtwork: boolean;
  onSend: (message: string) => void;
  onNewConsultation: () => void;
}

/**
 * The consultation with Melkov.
 *
 * The thread scrolls inside its own rail so the input stays pinned to the
 * bottom of the panel at every viewport size (FRONTEND_SPEC §17, §33) — the
 * one control that must never scroll out of reach.
 */
export function ChatPanel({
  messages,
  status,
  busy,
  hasArtwork,
  onSend,
  onNewConsultation,
}: ChatPanelProps) {
  const [draft, setDraft] = useState("");
  const railRef = useAutoScroll(`${messages.length}:${status}`);

  const handleSend = () => {
    const trimmed = draft.trim();
    if (!trimmed || busy) {
      return;
    }
    onSend(trimmed);
    setDraft("");
  };

  return (
    <Panel className="chat-panel max-sm:p-2.5">
      <div className="panel-title panel-title-row">
        <h2>Conversation with Melkov</h2>
        {messages.length > 0 ? (
          <button
            className="panel-action max-sm:px-2 max-sm:py-1.5"
            onClick={onNewConsultation}
            type="button"
          >
            New consultation
          </button>
        ) : null}
      </div>

      <div className="chat-rail max-sm:max-h-[58vh] max-sm:min-h-[240px]" ref={railRef}>
        {messages.length === 0 && !busy ? (
          <ChatEmptyState hasArtwork={hasArtwork} />
        ) : (
          <div className="chat-thread">
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
            {busy ? <AnalysisStatus status={status} /> : null}
          </div>
        )}
      </div>

      <ChatInput
        busy={busy}
        hasArtwork={hasArtwork}
        onChange={setDraft}
        onSend={handleSend}
        value={draft}
      />
    </Panel>
  );
}
