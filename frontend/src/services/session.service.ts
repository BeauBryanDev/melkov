const STORAGE_KEY = "aegis.session_id";

/**
 * Return this browser's conversation id, creating one on first visit.
 *
 * The backend keys chat history on `session_id` and holds it in process
 * memory, so persisting the id in `sessionStorage` keeps a conversation alive
 * across a page reload while still starting fresh in a new tab.
 */
export function getSessionId(): string {
  const existing = sessionStorage.getItem(STORAGE_KEY);
  if (existing) {
    return existing;
  }

  const created = createSessionId();
  sessionStorage.setItem(STORAGE_KEY, created);
  return created;
}

/** Forget the current id so the next call starts a new conversation. */
export function resetSessionId(): string {
  const created = createSessionId();
  sessionStorage.setItem(STORAGE_KEY, created);
  return created;
}

function createSessionId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `s-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}
