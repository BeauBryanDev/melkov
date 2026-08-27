import melkovHead from "../../assets/melkov_head.svg";

interface ChatPrinceAvatarProps {
  size?: number;
  className?: string;
}

/**
 * Melkov's portrait in the conversation.
 *
 * Uses the same `melkov_head.svg` as the masthead, so the expert wears one
 * face throughout the atelier rather than a second, drawn-in-code likeness.
 */
export function ChatPrinceAvatar({ size = 34, className }: ChatPrinceAvatarProps) {
  return (
    <span
      className={className ?? "chat-role-avatar"}
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      <img src={melkovHead} alt="" />
    </span>
  );
}
