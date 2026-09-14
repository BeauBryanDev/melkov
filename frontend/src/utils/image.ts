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
 * Longest side of an upload after downscaling.
 *
 * The backend resizes to 896 px before the VLM sees it and the classifier
 * works at a fraction of that, so pixels beyond this never reach a model —
 * they only make the base64 body bigger and the upload slower. 1024 keeps a
 * little margin over 896 so the preview in the frame still looks crisp.
 */
export const MAX_UPLOAD_DIM = 1024;

/** JPEG quality for the downscaled upload; visually lossless for paintings. */
const UPLOAD_JPEG_QUALITY = 0.9;

/**
 * Shrink an image so its longest side is at most `maxDim`, as a JPEG data URL.
 *
 * An image already within the limit is returned untouched, bytes and format
 * included. Any decoding or canvas failure also returns the original: a
 * downscale is an optimisation, never a reason to refuse a picture.
 *
 * @param dataUrl The image as read from the file.
 * @param maxDim Longest side allowed, in pixels.
 */
export async function downscaleDataUrl(
  dataUrl: string,
  maxDim = MAX_UPLOAD_DIM,
): Promise<string> {
  try {
    const image = await loadImage(dataUrl);
    const scale = maxDim / Math.max(image.naturalWidth, image.naturalHeight);
    if (!(scale < 1)) {
      return dataUrl;
    }
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(image.naturalWidth * scale);
    canvas.height = Math.round(image.naturalHeight * scale);
    const context = canvas.getContext("2d");
    if (!context) {
      return dataUrl;
    }
    // A white ground under transparent PNGs, since JPEG has no alpha.
    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", UPLOAD_JPEG_QUALITY);
  } catch {
    return dataUrl;
  }
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("The image could not be decoded."));
    image.src = src;
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
