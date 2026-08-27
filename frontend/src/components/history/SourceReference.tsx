import type { Citation } from "../../types/rag";

interface SourceReferenceProps {
  citation: Citation;
}

/**
 * The archive footer beneath a curatorial passage.
 *
 * Each line is omitted when its value is missing, and the component renders
 * nothing at all when it has neither — an empty "REFERENCE ID:" label reads
 * as a broken field rather than an absent one (FRONTEND_SPEC §25).
 */
export function SourceReference({ citation }: SourceReferenceProps) {
  if (!citation.source && !citation.referenceId) {
    return null;
  }

  return (
    <div className="history-source">
      {citation.source ? <span>Source: {citation.source}</span> : null}
      {citation.referenceId ? (
        <span title={citation.referenceId}>Query: {citation.referenceId}</span>
      ) : null}
    </div>
  );
}
