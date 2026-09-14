import { useCallback } from "react";
import { useArtworkStore } from "../stores/artwork.store";
import {
  downscaleDataUrl,
  fileToDataUrl,
  stripDataUrlPrefix,
  toDataUrl,
} from "../utils/image";
import { rejectionReason } from "../utils/validators";

/**
 * Places artwork in the frame.
 */
export function useArtwork() {
  // The store is a singleton, so the hooks are too.
  const store = useArtworkStore();
  const { setStatus, setError, placeArtwork, clearArtwork } = store;

  const acceptFile = useCallback(
    async (file: File | null) => {
      if (!file) {
        return;
      }

      const reason = rejectionReason(file);
      if (reason) {
        setError(reason);
        return;
      }

      setStatus("uploading");
      try {
        // Downscaled before it becomes base64: the backend resizes to 896 px
        // anyway, so a full-resolution upload only slows the wire.
        const dataUrl = await downscaleDataUrl(await fileToDataUrl(file));
        placeArtwork({
          imageBase64: stripDataUrlPrefix(dataUrl),
          previewUrl: dataUrl,
          fileName: file.name,
        });
      } catch {
        setError("That image could not be read. Please try another file.");
      }
    },
    [placeArtwork, setError, setStatus],
  );

  /** Hang an image FLUX produced, so it becomes the subject of the next turn. */
  const acceptGenerated = useCallback(
    (base64: string) => {
      placeArtwork({
        imageBase64: stripDataUrlPrefix(base64),
        previewUrl: toDataUrl(base64),
        generated: true,
      });
    },
    [placeArtwork],
  );

  const setDragging = useCallback(
    (dragging: boolean) => {
      // Only the empty and ready states may be overridden by a hover; an
      // in-flight upload or analysis must keep showing its own state.
      const current = useArtworkStore.getState().status;
      if (dragging) {
        if (current === "empty" || current === "ready" || current === "error") {
          setStatus("dragging");
        }
      } else if (current === "dragging") {
        setStatus(useArtworkStore.getState().previewUrl ? "ready" : "empty");
      }
    },
    [setStatus],
  );

  return {
    ...store,
    acceptFile,
    acceptGenerated,
    setDragging,
    clearArtwork,
  };
}
