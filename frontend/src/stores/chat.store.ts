import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ChatMessage, ChatStatus } from "../types/chat";
import { createId } from "../utils/format";

interface ChatStore {
  messages: ChatMessage[];
  status: ChatStatus;
  error: string | null;
  addMessage: (message: Omit<ChatMessage, "id" | "timestamp">) => void;
  setStatus: (status: ChatStatus) => void;
  setError: (error: string | null) => void;
  resetChat: () => void;
}

/**
 * The conversation.
 *
 * It starts genuinely empty — no greeting, no sample exchange, no fake
 * timestamps. The chat panel renders its own empty state instead, so nothing
 * on screen is ever mistaken for something Melkov actually said.
 */
/** Keep the transcript, drop base64 images: localStorage is ~5 MB and one upload can fill it. */
function forStorage(message: ChatMessage): ChatMessage {
  const { attachment: _attachment, generatedImage: _generated, ...rest } = message;
  return rest;
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set) => ({
      messages: [],
      status: "idle",
      error: null,

      addMessage: (message) =>
        set((state) => ({
          messages: [
            ...state.messages,
            { ...message, id: createId(message.role), timestamp: new Date().toISOString() },
          ],
        })),

      setStatus: (status) => set({ status }),

      setError: (error) => set({ error, status: error ? "error" : "idle" }),

      resetChat: () => set({ messages: [], status: "idle", error: null }),
    }),
    {
      name: "aegis.chat",
      partialize: (state) => ({ messages: state.messages.map(forStorage) }),
    },
  ),
);
