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
import { useRevealedText } from "./useRevealedText";

interface ChatMessageProps {
  message: ChatMessageType;
}

/** Every link in a reply opens in a new tab, so the consultation is never navigated away. */
const MARKDOWN_COMPONENTS: Components = {
  a: ({ node: _node, ...props }) => <a {...props} rel="noopener noreferrer" target="_blank" />,
};

/**
 * One turn of the consultation.
 */
export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  const time = formatTime(message.timestamp);
  // A freshly arrived reply is typed out over a couple of seconds; the
  // visitor's own message, a failed turn, and restored history show at once.
  const { text: replyText, revealing } = useRevealedText(
    isUser || message.failed ? "" : message.content,
    message.timestamp,
  );

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
      ) : message.failed ? (
        <div className="chat-body chat-body-rich">
          <ReactMarkdown components={MARKDOWN_COMPONENTS} remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        </div>
      ) : (
        <div className={`chat-body chat-body-rich${revealing ? " chat-body-revealing" : ""}`}>
          <ReactMarkdown components={MARKDOWN_COMPONENTS} remarkPlugins={[remarkGfm]}>
            {replyText}
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
