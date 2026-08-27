import type { ArtworkAnalysis } from "../../types/artwork";

interface ArtworkCaptionsProps {
  analysis: ArtworkAnalysis | null;
  fileName: string | null;
  generated: boolean;
  hasArtwork: boolean;
}

const FIELDS: { key: keyof ArtworkAnalysis; label: string }[] = [
  { key: "title", label: "Title" },
  { key: "artist", label: "Artist" },
  { key: "style", label: "Style" },
  { key: "date", label: "Date" },
];

/**
 * The museum catalogue plaque beneath the frame.
 *
 * Renders only the fields the application actually holds. `ChatResponse`
 * carries no catalogue metadata today, so with a picture hung but nothing
 * attributed the plaque names the source of the image and says plainly that
 * attribution is still pending — it never fills the gaps with an example
 * artist or date.
 */
export function ArtworkCaptions({
  analysis,
  fileName,
  generated,
  hasArtwork,
}: ArtworkCaptionsProps) {
  const entries = analysis
    ? FIELDS.map(({ key, label }) => ({ label, value: analysis[key] })).filter(
        (entry): entry is { label: string; value: string } =>
          typeof entry.value === "string" && entry.value.trim().length > 0,
      )
    : [];

  if (!hasArtwork) {
    return (
      <div className="art-caption art-caption-empty">
        <p>Awaiting an artwork</p>
        <span>Title · Artist · Style · Date</span>
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div className="art-caption">
        <p>{generated ? "Painted by Melkov" : (fileName ?? "Untitled work")}</p>
        <span>Attribution pending</span>
      </div>
    );
  }

  return (
    <dl className="art-caption art-plaque">
      {entries.map(({ label, value }) => (
        <div className="art-plaque-row" key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}
