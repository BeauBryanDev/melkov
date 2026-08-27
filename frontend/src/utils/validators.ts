import { MAX_IMAGE_BYTES } from "./image";

const ACCEPTED_TYPES = ["image/png", "image/jpeg", "image/webp", "image/gif"];

export function isImageFile(file: File): boolean {
  return file.type.startsWith("image/");
}

/**
 * Check a dropped or chosen file before it reaches the backend.
 *
 * @returns `null` when the file is acceptable, otherwise a museum-voiced
 *   reason to show in the frame's error state.
 */
export function rejectionReason(file: File): string | null {
  if (!isImageFile(file)) {
    return "Only paintings and photographs may be placed in the frame.";
  }
  if (ACCEPTED_TYPES.length > 0 && !ACCEPTED_TYPES.includes(file.type)) {
    return "That image format cannot be hung here. Use PNG, JPEG or WebP.";
  }
  if (file.size > MAX_IMAGE_BYTES) {
    return "That canvas is too large for the frame. Please offer a smaller image.";
  }
  return null;
}
