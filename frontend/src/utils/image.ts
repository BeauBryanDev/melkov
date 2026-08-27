/**
 * Ceiling on the base64 payload sent to `POST /chat`.
 *
 * The backend answers 413 above its own `MAX_IMAGE_B64_CHARS`; rejecting
 * oversized files here means the visitor learns immediately instead of after
 * a round trip. Kept conservative relative to the server's limit.
 */
export const MAX_IMAGE_BYTES = 8 * 1024 * 1024;

/** Read a file as a `data:` URL, suitable for both preview and upload. */
export function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("The file could not be read."));
    reader.onload = () => {
      if (typeof reader.result === "string") {
        resolve(reader.result);
      } else {
        reject(new Error("The file could not be read as an image."));
      }
    };
    reader.readAsDataURL(file);
  });
}

/**
 * Strip a `data:` prefix, leaving raw base64.
 *
 * The backend accepts either form, but sending the bare payload keeps the
 * request body honest about what it contains.
 */
export function stripDataUrlPrefix(dataUrl: string): string {
  const comma = dataUrl.indexOf(",");
  return dataUrl.startsWith("data:") && comma !== -1
    ? dataUrl.slice(comma + 1)
    : dataUrl;
}

/** Wrap raw base64 from the backend into a displayable PNG data URL. */
export function toDataUrl(base64: string): string {
  return base64.startsWith("data:") ? base64 : `data:image/png;base64,${base64}`;
}

/**
 * Decode base64 into a Blob.
 *
 * A blob URL is used for downloads rather than putting the data URL straight
 * on the anchor's href: a 1024x1024 PNG is a megabyte-plus of base64, and
 * some browsers refuse to download data URLs beyond a size limit.
 */
function base64ToBlob(base64: string, mimeType = "image/png"): Blob {
  const binary = atob(stripDataUrlPrefix(base64));
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return new Blob([bytes], { type: mimeType });
}

/**
 * Save an image the visitor is looking at to their machine.
 *
 * The object URL is revoked on the next tick rather than immediately — Firefox
 * cancels an in-flight download if its blob URL is released synchronously.
 *
 * @param base64 The image payload, with or without a `data:` prefix.
 * @param fileName Name to suggest in the save dialog, without extension.
 */
export function downloadPng(base64: string, fileName: string): void {
  const url = URL.createObjectURL(base64ToBlob(base64));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName.endsWith(".png") ? fileName : `${fileName}.png`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

/** A dated, filesystem-safe name for an artwork Melkov painted. */
export function artworkFileName(prefix = "melkov-artwork"): string {
  const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
  return `${prefix}-${stamp}`;
}
