import axios from "axios";

/**
 * Shared axios instance for the Melkov backend.
 *
 * The default base URL matches the uvicorn dev server documented in
 * CLAUDE.md. Override it with `VITE_API_BASE_URL` in `frontend/.env`.
 *
 * The timeout is deliberately long: a turn that reaches the VLM Space waits
 * on a ZeroGPU cold start, and one that reaches the RAG tool loads the
 * embedding model on first use. A short timeout would abort perfectly
 * healthy requests.
 */
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8009",
  timeout: 240_000,
  headers: {
    "Content-Type": "application/json",
  },
});
