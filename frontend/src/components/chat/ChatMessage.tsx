import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage as ChatMessageType } from "../../types/chat";
import { ChatPrinceAvatar } from "./ChatPrinceAvatar";
import { formatTime } from "../../utils/format";
import { toDataUrl } from "../../utils/image";
import { MetResults } from "./MetResults";
import { VideoResults } from "./VideoResults";
import { MuseumResults } from "../common/MuseumResults";
import { ToolTrace } from "./ToolTrace";

interface ChatMessageProps {
  message: ChatMessageType;
}

/** Every link in a reply opens in a new tab, so the consultation is never navigated away. */
const MARKDOWN_COMPONENTS: Components = {
  a: ({ node: _node, ...props }) => <a {...props} rel="noopener noreferrer" target="_blank" />,
};

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
          <ReactMarkdown components={MARKDOWN_COMPONENTS} remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
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
      {message.louvreResults?.length ? (
        <MuseumResults title="From the Louvre" works={message.louvreResults} />
      ) : null}
      {message.britishMuseumResults?.length ? (
        <MuseumResults title="From the British Museum" works={message.britishMuseumResults} />
      ) : null}
      {message.artAdvice?.length ? <VideoResults videos={message.artAdvice} /> : null}

      {message.tools?.length ? <ToolTrace tools={message.tools} /> : null}
    </article>
  );
}
