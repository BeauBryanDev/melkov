/**
 * Catalogue data for the artwork currently in the frame.
 *
 * Every field is optional: the backend does not yet return structured
 * catalogue metadata, so the plaque renders only the fields it actually has
 * and hides itself entirely when it has none. Nothing here is ever defaulted
 * to a sample value.
 */
export interface ArtworkAnalysis {
  title?: string | null;
  artist?: string | null;
  style?: string | null;
  date?: string | null;
  medium?: string | null;
}

/** The frame's lifecycle, per FRONTEND_SPEC §11. */
export type ArtworkStatus =
  | "empty"
  | "dragging"
  | "uploading"
  | "analyzing"
  | "ready"
  | "error";

export interface ArtworkState {
  /** Base64 payload sent to the backend with the next turn. */
  imageBase64: string | null;
  /** Object URL or data URL used for on-screen preview. */
  previewUrl: string | null;
  /** Original filename, shown as a fallback plaque line. */
  fileName: string | null;
  /** True when the image came from FLUX rather than an upload. */
  generated: boolean;
  analysis: ArtworkAnalysis | null;
  status: ArtworkStatus;
  error: string | null;
}
