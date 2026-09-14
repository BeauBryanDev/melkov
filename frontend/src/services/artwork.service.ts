import type { ArtworkReadRequestBody, ArtworkReadResponseBody } from "../types/api";
import { api } from "./api";

/**
 * Read the artwork in the frame ahead of the first question (`POST /artwork/read`).
 *
 * The backend runs the vision model and the classifier and caches both under
 * the image's hash, so the first chat turn finds them already inlined and
 * costs what a follow-up costs. Errors propagate: the caller falls back to
 * sending the image with the turn, which is what happened before this existed.
 */
export async function readArtwork(
  body: ArtworkReadRequestBody,
): Promise<ArtworkReadResponseBody> {
  const response = await api.post<ArtworkReadResponseBody>("/artwork/read", body);
  return response.data;
}
