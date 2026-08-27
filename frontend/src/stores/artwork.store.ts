import { create } from "zustand";
import type { ArtworkAnalysis, ArtworkState, ArtworkStatus } from "../types/artwork";

interface ArtworkStore extends ArtworkState {
  setStatus: (status: ArtworkStatus) => void;
  setError: (error: string | null) => void;
  /** Place an image in the frame, from an upload or from FLUX. */
  placeArtwork: (payload: {
    imageBase64: string;
    previewUrl: string;
    fileName?: string | null;
    generated?: boolean;
  }) => void;
  setAnalysis: (analysis: ArtworkAnalysis | null) => void;
  clearArtwork: () => void;
}

/**
 * The artwork currently in the frame.
 *
 * The initial state is deliberately empty on every field. Earlier revisions
 * seeded this with a sample Impressionist attribution, which rendered as real
 * production content — FRONTEND_SPEC §37 forbids it.
 */
const initialState: ArtworkState = {
  imageBase64: null,
  previewUrl: null,
  fileName: null,
  generated: false,
  analysis: null,
  status: "empty",
  error: null,
};

export const useArtworkStore = create<ArtworkStore>((set) => ({
  ...initialState,

  setStatus: (status) => set({ status }),

  setError: (error) => set({ error, status: error ? "error" : "empty" }),

  placeArtwork: ({ imageBase64, previewUrl, fileName = null, generated = false }) =>
    set({
      imageBase64,
      previewUrl,
      fileName,
      generated,
      status: "ready",
      error: null,
    }),

  setAnalysis: (analysis) => set({ analysis }),

  clearArtwork: () => set({ ...initialState }),
}));
