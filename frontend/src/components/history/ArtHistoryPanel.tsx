import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ArtHistoryEntry } from "../../types/rag";
import { Panel } from "../ui/Panel";
import { SourceReference } from "./SourceReference";
import { EmptyState } from "../common/EmptyState";
import { IlluminatedLetter } from "../ui/Ornaments";

interface ArtHistoryPanelProps {
  title?: string;
  entry: ArtHistoryEntry | null;
}

/**
 * The curatorial archive card.
 *
 * Fills only when a turn actually consulted the art-history corpus — the
 * frontend reads `tools_used` for `query_art_history_tool` and shows that
 * turn's grounded passage. Until then it stays empty rather than displaying
 * the Impressionism paragraph the mockup uses as sample copy.
 */
export function ArtHistoryPanel({ title = "Art History", entry }: ArtHistoryPanelProps) {
  const dropCap = entry?.content.trim().charAt(0).toUpperCase() || "A";
  const body = entry ? entry.content.trim().slice(1) : "";

  return (
    <Panel className="history-panel max-sm:p-2.5">
      <div className="panel-title panel-title-row">
        <h2>{title}</h2>
      </div>

      {entry ? (
        <>
          <div className="history-card">
            <IlluminatedLetter letter={dropCap} />
            <div className="history-body">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{body}</ReactMarkdown>
            </div>
          </div>
          <SourceReference citation={entry.citation} />
        </>
      ) : (
        <EmptyState
          title="The archive is closed"
          body="Ask Melkov about a movement, a technique, or a period, and the passage he draws on will be recorded here."
        />
      )}
    </Panel>
  );
}
