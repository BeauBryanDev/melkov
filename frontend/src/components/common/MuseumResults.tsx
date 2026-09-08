import type { MuseumWork } from "../../types/api";

interface MuseumResultsProps {
  /** Heading, e.g. "From the Louvre". */
  title: string;
  works: MuseumWork[];
}

/** Year of a Wikidata timestamp like "1830-01-01T00:00:00Z"; other dates pass through. */
function displayDate(date?: string | null): string | null {
  if (!date) return null;
  const match = /^(-?)(\d{4})-\d{2}-\d{2}T/.exec(date);
  if (!match) return date;
  return match[1] ? `${match[2]} BC` : match[2];
}

/** Shared card list for any museum's works. Absent fields are omitted, never filled in. */
export function MuseumResults({ title, works }: MuseumResultsProps) {
  if (works.length === 0) return null;

  return (
    <section className="met-results">
      <h3 className="met-results-title">{title}</h3>
      <ul>
        {works.map((work, index) => {
          const meta = [work.artist, displayDate(work.date), work.medium].filter(Boolean);
          const name = work.title ?? "Untitled";
          return (
            <li className="met-card" key={work.object_url ?? index}>
              {work.image_url ? (
                <img alt={name} loading="lazy" src={work.image_url} />
              ) : (
                <span className="met-card-plate" aria-hidden="true" />
              )}
              <div className="met-card-body">
                <p className="met-card-title">
                  {work.object_url ? (
                    <a href={work.object_url} rel="noreferrer" target="_blank">{name}</a>
                  ) : name}
                </p>
                {meta.length > 0 ? <p className="met-card-meta">{meta.join(" · ")}</p> : null}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
