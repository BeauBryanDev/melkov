import type { MetRecord, ToolCallLog } from "./api";

export type ChatRole = "user" | "assistant";

/**
 * One rendered turn in the conversation.
 *
 * Everything here comes from either the user's own input or the backend
 * response — there are no placeholder or demo messages anywhere in the app.
 */
export interface ChatMessage {
  id: string;
  role: ChatRole;
  /** Display name: "Melkov" or "You". */
  name: string;
  content: string;
  /** ISO timestamp; formatted for display at render time. */
  timestamp: string;
  /** Tools the agent used to produce this reply (assistant turns only). */
  tools?: ToolCallLog[];
  /** Base64 image the user attached to this turn (user turns only). */
  attachment?: string | null;
  /** Base64 image FLUX produced for this turn (assistant turns only). */
  generatedImage?: string | null;
  /** MET records returned for this turn (assistant turns only). */
  metResults?: MetRecord[] | null;
  /** Set when the turn failed; rendered in the restrained error style. */
  failed?: boolean;
}

/**
 * The conversation's lifecycle, driving every visual state in the chat panel.
 *
 * `analyzing` is distinguished from `thinking` because it is the one case
 * where the user is waiting on the VLM Space, which cold-starts and can take
 * the better part of a minute.
 */
export type ChatStatus = "idle" | "sending" | "thinking" | "analyzing" | "error";
