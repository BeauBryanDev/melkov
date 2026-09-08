import type { MetRecord } from "../../types/api";
import { MuseumResults } from "../common/MuseumResults";

interface MetResultsProps {
  records: MetRecord[];
}

/** Met works. Images show only for public-domain records, the Met's own reproduction flag. */
export function MetResults({ records }: MetResultsProps) {
  const works = records.map((record) => ({
    title: record.title,
    artist: record.artist,
    date: record.date,
    medium: record.medium,
    image_url: record.is_public_domain ? (record.image_url_small ?? record.image_url) : null,
    object_url: record.object_url,
  }));
  return <MuseumResults title="From the Met collection" works={works} />;
}
