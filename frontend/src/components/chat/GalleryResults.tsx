import type { GalleryWork, MuseumWork } from "../../types/api";
import { MuseumResults } from "../common/MuseumResults";

interface GalleryResultsProps {
  works: GalleryWork[];
}

/**
 * Public base for the S3-hosted training gallery (bucket, CloudFront, or a
 * backend proxy). Unset until the project is deployed on AWS; the cards then
 * render the plain plate instead of a broken image.
 */
const GALLERY_BASE_URL = (import.meta.env.VITE_GALLERY_BASE_URL as string | undefined)?.replace(/\/$/, "");

/** Maps Melkov's own gallery rows onto the shared museum card list. Shown in chat only, never in the frame. */
export function GalleryResults({ works }: GalleryResultsProps) {
  const mapped: MuseumWork[] = works.map((work) => ({
    title: work.caption ? truncate(work.caption, 90) : work.id,
    artist: work.artist && work.artist !== "Unknown Artist" ? work.artist : null,
    date: null,
    medium: work.style,
    image_url: GALLERY_BASE_URL ? `${GALLERY_BASE_URL}/${work.s3_key}` : null,
    object_url: null,
  }));

  return <MuseumResults title="From Melkov's own gallery" works={mapped} />;
}

function truncate(text: string, max: number): string {
  return text.length <= max ? text : `${text.slice(0, max).trimEnd()}…`;
}
