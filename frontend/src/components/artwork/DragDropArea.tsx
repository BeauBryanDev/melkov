import { useId, useRef } from "react";
import type { ChangeEvent } from "react";
import palette from "../../assets/art_palette.svg";
import type { ArtworkStatus } from "../../types/artwork";
import { UploadOver } from "./UploadOver";
import { Spinner } from "../common/Spinner";

interface DragDropAreaProps {
  status: ArtworkStatus;
  previewUrl: string | null;
  isDragging: boolean;
  error: string | null;
  onFile: (file: File) => void;
  onClear: () => void;
}

/**
 * The frame's interior: one surface rendering every artwork state
 * (FRONTEND_SPEC §11).
 *
 * The file input is a real, focusable `<input type="file">` rather than a
 * click-handled `<div>`, so keyboard and screen-reader users reach the same
 * affordance the pointer does.
 */
export function DragDropArea({
  status,
  previewUrl,
  isDragging,
  error,
  onFile,
  onClear,
}: DragDropAreaProps) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      onFile(file);
    }
    // Reset so choosing the same file twice still fires a change event.
    event.target.value = "";
  };

  const busy = status === "uploading" || status === "analyzing";

  return (
    <div
      className="frame-stage max-sm:min-h-[240px] max-sm:p-3.5"
      data-state={isDragging ? "dragging" : status}
    >
      <input
        accept="image/png,image/jpeg,image/webp"
        className="frame-file-input"
        id={inputId}
        onChange={handleChange}
        ref={inputRef}
        type="file"
      />

      {previewUrl ? (
        <>
          <img className="frame-preview" src={previewUrl} alt="The artwork in the frame" />
          {busy ? (
            <div className="frame-veil" role="status">
              <Spinner />
              <p className="frame-veil-copy">
                {status === "analyzing" ? "Melkov is examining the work" : "Placing the canvas"}
              </p>
            </div>
          ) : null}
          <div className="frame-actions max-sm:right-3 max-sm:bottom-3">
            <button
              className="frame-action"
              onClick={() => inputRef.current?.click()}
              type="button"
            >
              Replace
            </button>
            <button className="frame-action" onClick={onClear} type="button">
              Remove
            </button>
          </div>
        </>
      ) : (
        <div className="frame-stage-content">
          {busy ? (
            <div className="frame-empty-status" role="status">
              <Spinner />
              <p className="upload-subheading">Placing the canvas</p>
            </div>
          ) : (
            <>
              <div className="upload-icon max-sm:h-16 max-sm:w-16" aria-hidden="true">
                <img src={palette} alt="" />
              </div>
              <UploadOver dragging={isDragging} />
              <label className="upload-trigger max-sm:w-full" htmlFor={inputId}>
                <span className="royal-button royal-button-secondary max-sm:w-full max-sm:justify-center">
                  Browse the collection
                </span>
              </label>
            </>
          )}
        </div>
      )}

      {error ? (
        <p className="frame-error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
