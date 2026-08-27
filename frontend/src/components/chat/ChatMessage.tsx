import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage as ChatMessageType } from "../../types/chat";
import { ChatPrinceAvatar } from "./ChatPrinceAvatar";
import { formatTime } from "../../utils/format";
import { toDataUrl } from "../../utils/image";
import { MetResults } from "./MetResults";
import { ToolTrace } from "./ToolTrace";

interface ChatMessageProps {
  message: ChatMessageType;
}

/**
 * One turn of the consultation.
 *
 * Melkov's replies carry the gold accent, the portrait, and full width; the
 * visitor's are narrower and quieter, so the expert's voice stays dominant
 * (FRONTEND_SPEC §15, §16). Replies are markdown because the agent writes
 * emphasis and lists, which would otherwise show as literal asterisks.
 */
export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  const time = formatTime(message.timestamp);

  return (
    <article
      className={[
        "chat-message",
        isUser ? "chat-message-user" : "chat-message-melkov",
        message.failed ? "chat-message-failed" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <div className="chat-header">
        <div className="chat-role">
          {isUser ? null : <ChatPrinceAvatar size={34} />}
          <span>{message.name}</span>
        </div>
        {time ? <time dateTime={message.timestamp}>{time}</time> : null}
      </div>

      {isUser ? (
        <p className="chat-body">{message.content}</p>
      ) : (
        <div className="chat-body chat-body-rich">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        </div>
      )}

      {message.attachment ? (
        <img
          alt="The artwork you attached to this message"
          className="chat-attachment"
          src={toDataUrl(message.attachment)}
        />
      ) : null}

      {/* No download control here: saving lives in the frame only. */}
      {message.generatedImage ? (
        <img
          alt="The artwork Melkov painted for this reply"
          className="chat-attachment"
          src={toDataUrl(message.generatedImage)}
        />
      ) : null}

      {message.metResults?.length ? <MetResults records={message.metResults} /> : null}

      {message.tools?.length ? <ToolTrace tools={message.tools} /> : null}
    </article>
  );
}
