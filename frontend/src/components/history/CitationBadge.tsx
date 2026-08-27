interface CitationBadgeProps {
  children: string;
}

export function CitationBadge({ children }: CitationBadgeProps) {
  return <span className="citation-badge">{children}</span>;
}
