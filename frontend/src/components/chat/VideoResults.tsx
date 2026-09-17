import type { ArtAdviceVideo } from "../../types/api";

interface VideoResultsProps {
  videos: ArtAdviceVideo[];
}
// came from youtube url
const VIDEO_ID = /[?&]v=([\w-]+)/;

function thumbnail(url: string): string | null {
  const id = VIDEO_ID.exec(url)?.[1];
  return id ? `https://i.ytimg.com/vi/${id}/mqdefault.jpg` : null;
}

/** Painting-technique videos from the trusted artist channels. */
export function VideoResults({ videos }: VideoResultsProps) {
  if (videos.length === 0) return null;

  return (
    <section className="met-results">
      <h3 className="met-results-title">From the studio masters</h3>
      <ul>
        {videos.map((video) => {
          const thumb = thumbnail(video.url);
          return (
            <li className="met-card video-card" key={video.url}>
              {thumb ? (
                <img alt="" loading="lazy" src={thumb} />
              ) : (
                <span className="met-card-plate" aria-hidden="true" />
              )}
              <div className="met-card-body">
                <p className="met-card-title">
                  <a href={video.url} rel="noreferrer" target="_blank">{video.title}</a>
                </p>
                <p className="met-card-meta">
                  {video.channel}
                  {video.description_snippet ? ` · ${video.description_snippet}` : ""}
                </p>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
