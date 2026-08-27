import { artworkFileName, downloadPng } from "../../utils/image";

interface DownloadArtworkButtonProps {
  /** The image payload, with or without a `data:` prefix. */
  base64: string;
  /** Optional filename stem; a timestamp is appended. */
  namePrefix?: string;
  className?: string;
  label?: string;
}

/**
 * Saves an artwork Melkov painted to the visitor's machine as a PNG.
 *
 * A button rather than an `<a download>`: the payload arrives as base64 in
 * the chat response, so there is no URL to link to until one is minted from
 * a blob at click time.
 */
export function DownloadArtworkButton({
  base64,
  namePrefix = "melkov-artwork",
  className = "frame-action",
  label = "Download PNG",
}: DownloadArtworkButtonProps) {
  return (
    <button
      className={className}
      onClick={() => downloadPng(base64, artworkFileName(namePrefix))}
      title="Save this artwork as a PNG"
      type="button"
    >
      {label}
    </button>
  );
}
