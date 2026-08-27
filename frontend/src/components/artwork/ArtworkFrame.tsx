import brush1 from "../../assets/painting_brush1.svg";
import brush2 from "../../assets/painting_brush2.svg";
import type { ArtworkAnalysis, ArtworkStatus } from "../../types/artwork";
import { ArtworkCaptions } from "./ArtworkCaptions";
import { DragDropArea } from "./DragDropArea";
import { Panel } from "../ui/Panel";
import { GildedFrameCorners } from "../ui/Ornaments";
import { useDragDrop } from "../../hooks/useDragDrop";
import { DownloadArtworkButton } from "../common/DownloadArtworkButton";

interface ArtworkFrameProps {
  analysis: ArtworkAnalysis | null;
  previewUrl: string | null;
  /** Raw payload of the hung artwork, used for the PNG download. */
  imageBase64: string | null;
  fileName: string | null;
  generated: boolean;
  status: ArtworkStatus;
  error: string | null;
  onFile: (file: File) => void;
  onClear: () => void;
}

/**
 * The museum frame — the highest-ornamentation surface in the atelier
 * (FRONTEND_SPEC §28) and the primary visual object on the page.
 *
 * The frame owns the drag state so the gold highlight can wrap the whole
 * gilded shell rather than only the drop target inside it.
 */
export function ArtworkFrame({
  analysis,
  previewUrl,
  imageBase64,
  fileName,
  generated,
  status,
  error,
  onFile,
  onClear,
}: ArtworkFrameProps) {
  const busy = status === "uploading" || status === "analyzing";
  const { isDragging, dragHandlers } = useDragDrop({ onFile, disabled: busy });

  const shellState = isDragging ? "dragging" : status;

  return (
    <Panel className="frame-panel max-sm:p-2.5">
      <div className="panel-title">
        <h2>The Frame</h2>
        <p>Upload or generate an artwork</p>
      </div>

      <div
        className="frame-stage-shell max-sm:p-2 max-sm:rounded-xl"
        data-state={shellState}
        {...dragHandlers}
      >
        <GildedFrameCorners />
        <DragDropArea
          error={error}
          isDragging={isDragging}
          onClear={onClear}
          onFile={onFile}
          previewUrl={previewUrl}
          status={status}
        />
      </div>

      {/* Directly beneath the canvas, above the catalogue plaque. Offered for
          any hung artwork, but worded for the ones Melkov painted. */}
      {imageBase64 ? (
        <div className="frame-download max-sm:[&>button]:w-full">
          <DownloadArtworkButton
            base64={imageBase64}
            className="royal-button royal-button-secondary"
            label={generated ? "Download this artwork" : "Download image"}
            namePrefix={generated ? "melkov-artwork" : "aegis-artwork"}
          />
        </div>
      ) : null}

      <ArtworkCaptions
        analysis={analysis}
        fileName={fileName}
        generated={generated}
        hasArtwork={Boolean(previewUrl)}
      />

      <div className="frame-decor frame-decor-left" aria-hidden="true">
        <img src={brush1} alt="" />
      </div>
      <div className="frame-decor frame-decor-right" aria-hidden="true">
        <img src={brush2} alt="" />
      </div>
    </Panel>
  );
}
