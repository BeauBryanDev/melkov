import { useCallback } from "react";
import { useArtworkStore } from "../stores/artwork.store";
import { fileToDataUrl, stripDataUrlPrefix, toDataUrl } from "../utils/image";
import { rejectionReason } from "../utils/validators";

/**
 * Places artwork in the frame.
 *
 * Reading the file produces a `data:` URL that serves as both the on-screen
 * preview and — with its prefix stripped — the `image_base64` sent with the
 * next chat turn. No analysis is fabricated here: the frame holds the picture
 * and nothing else until Melkov actually says something about it.
 */
export function useArtwork() {
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
        const dataUrl = await fileToDataUrl(file);
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
