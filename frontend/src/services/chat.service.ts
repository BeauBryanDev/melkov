import axios from "axios";
import type { ChatRequestBody, ChatResponseBody } from "../types/api";
import { api } from "./api";

/**
 * An error the chat panel can show the visitor without breaking character.
 *
 * The technical detail is kept separately so it can be logged or surfaced in
 * a debug affordance, but never printed as the user-facing sentence.
 */
export class ChatError extends Error {
  readonly detail: string | null;

  constructor(message: string, detail: string | null = null) {
    super(message);
    this.name = "ChatError";
    this.detail = detail;
  }
}

/**
 * Run one conversational turn against `POST /chat`.
 *
 * `session_id` is required by `ChatRequest`; sending only `message` returns a
 * 422. The image travels as base64 in the body, matching the backend's
 * `image_base64` field.
 *
 * @throws ChatError with a museum-voiced message on any failure.
 */
export async function sendChatMessage(
  body: ChatRequestBody,
): Promise<ChatResponseBody> {
  try {
    const response = await api.post<ChatResponseBody>("/chat", body);
    return response.data;
  } catch (error) {
    throw toChatError(error);
  }
}

/** Ask the backend to forget a conversation. Failure here is not worth surfacing. */
export async function clearSession(sessionId: string): Promise<void> {
  try {
    await api.delete(`/session/${encodeURIComponent(sessionId)}`);
  } catch {
    // The session is in-process and dies with the server anyway; a failed
    // clear leaves nothing the visitor needs to act on.
  }
}

/** Translate an axios failure into the atelier's own voice. */
function toChatError(error: unknown): ChatError {
  if (!axios.isAxiosError(error)) {
    return new ChatError(
      "Melkov could not complete that thought. Please try again.",
      error instanceof Error ? error.message : null,
    );
  }

  const detail =
    typeof error.response?.data?.detail === "string"
      ? error.response.data.detail
      : error.message;

  if (error.code === "ECONNABORTED") {
    return new ChatError(
      "Melkov is still deliberating and did not answer in time. Please ask again.",
      detail,
    );
  }
  if (!error.response) {
    return new ChatError(
      "The atelier is not answering. Confirm the Melkov service is running.",
      detail,
    );
  }

  switch (error.response.status) {
    case 413:
      return new ChatError(
        "That canvas is too large for the frame. Please offer a smaller image.",
        detail,
      );
    case 422:
      return new ChatError(
        "Melkov could not read that request. Please rephrase and try again.",
        detail,
      );
    case 502:
      return new ChatError(
        "Melkov set down his brush mid-thought. Please ask again in a moment.",
        detail,
      );
    default:
      return new ChatError(
        "Melkov could not complete that consultation. Please try again.",
        detail,
      );
  }
}
