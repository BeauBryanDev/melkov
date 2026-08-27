/**
 * Analysis types for the lower panels.
 *
 * The backend does not currently classify style, score confidence, or emit
 * discrete visual observations — `ChatResponse` carries prose plus artifacts.
 * These interfaces exist so the panels are already state-driven when those
 * fields arrive; until then the panels render their empty states. Per
 * FRONTEND_SPEC §37 no sample values are supplied anywhere.
 */

/** One row of the style classification chart. `score` is 0–1. */
export interface StylePrediction {
  label: string;
  score: number;
}

/** A single observation Melkov made about the picture surface. */
export interface VisualObservation {
  /** Short uppercase label, e.g. "LIGHT". */
  label: string;
  /** The observation itself, e.g. "Natural illumination". */
  value: string;
}

/** Where an art-history passage came from. */
export interface Citation {
  source: string | null;
  referenceId: string | null;
}

/**
 * The vision model's own account of the picture.
 *
 * Held as prose because that is what the model returns. Splitting it into
 * LIGHT / COLOUR / BRUSHWORK rows would be the frontend asserting a
 * structure the model never produced.
 */
export interface VlmReading {
  text: string;
  /** Which model produced it, for the panel's attribution line. */
  source: string;
}

/** A curatorial passage retrieved from the art-history corpus. */
export interface ArtHistoryEntry {
  content: string;
  citation: Citation;
}
