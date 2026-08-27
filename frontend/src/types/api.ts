/**
 * Wire types for the Melkov backend (`app/schemas/chat.py`).
 *
 * These mirror the FastAPI models exactly. If a field is not listed here, the
 * backend does not send it — the UI must render an empty state rather than
 * invent a value.
 */

/** A single tool invocation, as reported by `ChatResponse.tools_used`. */
export interface ToolCallLog {
  tool: string;
  input_summary: string;
}

/** POST /chat request body. `session_id` is required — omitting it returns 422. */
export interface ChatRequestBody {
  message: string;
  session_id: string;
  /** Raw base64, with or without a `data:` prefix. */
  image_base64?: string | null;
}

/** POST /chat response body. */
export interface ChatResponseBody {
  reply: string;
  session_id: string;
  tools_used: ToolCallLog[];
  generated_image_base64: string | null;
  met_results: MetRecord[] | null;
  /**
   * The fine-tuned Qwen2.5-VL's description of the attached image, verbatim.
   * Non-null only when the vision tool ran and succeeded on this turn.
   */
  vlm_description: string | null;
  /**
   * The style classifier's top-k scores for the attached image. Non-null only
   * when the classifier tool ran and succeeded on this turn.
   */
  style_analysis: StyleIdentification | null;
}

/**
 * One row of the style classifier's answer.
 *
 * Note the field is `probability`, not `score` — this is the wire shape.
 * `types/rag.ts :: StylePrediction` is the display shape the chart consumes;
 * `useChat` maps between them.
 */
export interface StyleProbability {
  label: string;
  /** Softmax weight, 0–1. */
  probability: number;
}

/**
 * The classifier's full answer, as returned by both `POST /style/identify`
 * and `ChatResponse.style_analysis` — one shape whichever path produced it.
 */
export interface StyleIdentification {
  /** Which classifier answered, e.g. "melkov-art-style-cnn". */
  model: string;
  /** Ranked highest probability first. */
  predictions: StyleProbability[];
  top_k: number;
}

/** POST /style/identify request body. */
export interface StyleRequestBody {
  image_base64: string;
  /** How many ranked styles to return; defaults to 3 server-side. */
  top_k?: number;
}

/**
 * One artwork from the MET Open Access API, as shaped by
 * `app/tools/met_search.py`. Almost every field can be null, so all are
 * optional here.
 */
export interface MetRecord {
  object_id?: number | null;
  title?: string | null;
  artist?: string | null;
  artist_bio?: string | null;
  artist_nationality?: string | null;
  date?: string | null;
  medium?: string | null;
  dimensions?: string | null;
  culture?: string | null;
  period?: string | null;
  classification?: string | null;
  department?: string | null;
  country?: string | null;
  tags?: string[] | null;
  image_url?: string | null;
  image_url_small?: string | null;
  object_url?: string | null;
  credit_line?: string | null;
  is_public_domain?: boolean | null;
}

/** The names the backend reports in `tools_used[].tool`. */
export const TOOL_NAMES = {
  describe: "describe_artwork_tool",
  generate: "generate_artwork_tool",
  met: "search_met_artworks_tool",
  history: "query_art_history_tool",
  style: "identify_art_style_tool",
} as const;
