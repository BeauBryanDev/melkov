import type { KeyboardEvent } from "react";
import trumpet from "../../assets/golden_trump.svg";
import { CHAT_PLACEHOLDER } from "../../utils/constant";
import { RoyalButton } from "../ui/RoyalButton";

interface ChatInputProps {
  value: string;
  busy: boolean;
  hasArtwork: boolean;
  onChange: (value: string) => void;
  onSend: () => void;
  placeholder?: string;
}

/**
 * The consultation input, permanently docked at the foot of the chat panel.
 *
 * A textarea rather than a single-line input: questions about a painting run
 * long, and the visitor should be able to see what they wrote. Enter sends,
 * Shift+Enter breaks the line — the convention for this control.
 */
export function ChatInput({
  value,
  busy,
  hasArtwork,
  onChange,
  onSend,
  placeholder = CHAT_PLACEHOLDER,
}: ChatInputProps) {
  const canSend = value.trim().length > 0 && !busy;

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSend();
    }
  };

  return (
    <div className="chat-input max-sm:gap-2">
      <span className="chat-input-ornament" aria-hidden="true">
        <img src={trumpet} alt="" />
      </span>

      <div className="chat-input-field">
        <textarea
          aria-label="Ask Melkov about this artwork"
          disabled={busy}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={2}
          value={value}
        />
        {hasArtwork ? (
          <p className="chat-input-note">The work in the frame travels with your question.</p>
        ) : null}
      </div>

      <RoyalButton
        aria-label="Send your question to Melkov"
        className="ask-button max-sm:w-full max-sm:py-3.5"
        disabled={!canSend}
        onClick={onSend}
        type="button"
      >
        {busy ? "Deliberating" : "Ask Melkov"}
      </RoyalButton>
    </div>
  );
}
