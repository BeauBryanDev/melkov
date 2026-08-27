import type { MetRecord } from "../../types/api";

interface MetResultsProps {
  records: MetRecord[];
}

/**
 * Real works returned by the Met Open Access API.
 *
 * Every line is drawn from the record and omitted when absent — the Met's
 * fields are frequently null, and an "artist unknown" placeholder would read
 * as an attribution the museum never made. Images render only for public
 * domain works, which is the flag the Met itself uses to mark them free to
 * reproduce.
 */
export function MetResults({ records }: MetResultsProps) {
  if (records.length === 0) {
    return null;
  }

  return (
    <section className="met-results">
      <h3 className="met-results-title">From the Met collection</h3>
      <ul>
        {records.map((record, index) => {
          const image = record.is_public_domain
            ? (record.image_url_small ?? record.image_url)
            : null;
          const meta = [record.artist, record.date, record.medium].filter(Boolean);

          return (
            <li className="met-card" key={record.object_id ?? index}>
              {image ? (
                <img alt={record.title ?? "Artwork from the Met collection"} src={image} />
              ) : (
                <span className="met-card-plate" aria-hidden="true" />
              )}
              <div className="met-card-body">
                <p className="met-card-title">
                  {record.object_url ? (
                    <a href={record.object_url} rel="noreferrer" target="_blank">
                      {record.title ?? "Untitled"}
                    </a>
                  ) : (
                    (record.title ?? "Untitled")
                  )}
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
