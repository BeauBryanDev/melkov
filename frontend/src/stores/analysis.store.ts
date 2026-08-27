import { create } from "zustand";
import type {
  ArtHistoryEntry,
  StylePrediction,
  VisualObservation,
  VlmReading,
} from "../types/rag";

interface AnalysisStore {
  /** Style classification, ordered highest score first. Null until scored. */
  styles: StylePrediction[] | null;
  /** Discrete observations about the picture surface. Null until provided. */
  observations: VisualObservation[] | null;
  /** The curatorial passage retrieved for the most recent turn. */
  history: ArtHistoryEntry | null;
  /** The vision model's verbatim reading of the artwork in the frame. */
  reading: VlmReading | null;
  setStyles: (styles: StylePrediction[] | null) => void;
  setObservations: (observations: VisualObservation[] | null) => void;
  setHistory: (history: ArtHistoryEntry | null) => void;
  setReading: (reading: VlmReading | null) => void;
  resetAnalysis: () => void;
}

/**
 * Everything the lower panels display.
 *
 * `styles` and `observations` stay null until the backend actually returns
 * them — `ChatResponse` carries no classification or observation fields yet,
 * so those panels show their empty states rather than sample numbers. The
 * setters exist so wiring them up later is a one-line change in `useChat`.
 */
export const useAnalysisStore = create<AnalysisStore>((set) => ({
  styles: null,
  observations: null,
  history: null,
  reading: null,
  setStyles: (styles) => set({ styles }),
  setObservations: (observations) => set({ observations }),
  setHistory: (history) => set({ history }),
  setReading: (reading) => set({ reading }),
  resetAnalysis: () =>
    set({ styles: null, observations: null, history: null, reading: null }),
}));
