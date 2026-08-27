import { FRAME_EMPTY_HEADING, FRAME_EMPTY_HINT } from "../../utils/constant";

interface UploadOverProps {
  dragging?: boolean;
}

/** The frame's invitation copy, which changes only while a file is over it. */
export function UploadOver({ dragging = false }: UploadOverProps) {
  return (
    <div className="upload-copy">
      <p className="upload-heading">
        {dragging ? "Release to hang the painting" : FRAME_EMPTY_HEADING}
      </p>
      <p className="upload-subheading">{dragging ? " " : FRAME_EMPTY_HINT}</p>
    </div>
  );
}
