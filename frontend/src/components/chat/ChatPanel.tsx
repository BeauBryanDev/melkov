import { useState } from "react";
import type {
  ChatMessage as ChatMessageType,
  ChatStatus,
} from "../../types/chat";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { ChatEmptyState } from "./ChatEmptyState";
import { AnalysisStatus } from "./AnalysisStatus";
import { Panel } from "../ui/Panel";
import { useAutoScroll } from "../../hooks/useAutoScroll";
import { useDragDrop } from "../../hooks/useDragDrop";

interface ChatPanelProps {
  messages: ChatMessageType[];
  status: ChatStatus;
  busy: boolean;
  hasArtwork: boolean;
  onSend: (message: string) => void;
  /** The visitor has started writing: a chance to read the artwork ahead of the question. */
  onComposing?: () => void;
  onNewConsultation: () => void;
  /** Hangs a file dropped onto the chat in the frame, via the same path the frame uses. */
  onFile: (file: File) => void;
}

/**
 * The consultation with Melkov.
 * The whole panel is also a drop target: a picture dragged onto the
 * conversation is hung in the frame exactly as if it had been dropped there,
 * so the visitor never has to leave the chat to change the subject. A drop is
 * ignored while a turn is in flight — the image in the frame must not change
 * under a question that has already been sent.
 */
export function ChatPanel({
  messages,
  status,
  busy,
  hasArtwork,
  onSend,
  onComposing,
  onNewConsultation,
  onFile,
}: ChatPanelProps) {
  const [draft, setDraft] = useState("");

  const handleDraft = (value: string) => {
    setDraft(value);
    if (value.trim()) {
      onComposing?.();
    }
  };
  const railRef = useAutoScroll(`${messages.length}:${status}`);
  const { isDragging, dragHandlers } = useDragDrop({ onFile, disabled: busy });

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
      <div
        className="chat-drop-zone"
        data-state={isDragging ? "dragging" : "idle"}
        {...dragHandlers}
      >
        {isDragging ? (
          <div className="chat-drop-overlay" aria-hidden="true">
            <p>Release to hang this work in the frame</p>
          </div>
        ) : null}
        <div className="panel-title panel-title-row">
          <h2>Chat with Melkov</h2>
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

        <div
          className="chat-rail max-sm:max-h-[58vh] max-sm:min-h-[240px]"
          ref={railRef}
        >
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
          onChange={handleDraft}
          onSend={handleSend}
          value={draft}
        />
      </div>
    </Panel>
  );
}
