import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  body: string;
  children?: ReactNode;
}

/**
 * The shared "nothing here yet" surface.
 *
 * Every panel that can be empty uses this one, so an unfilled panel reads as
 * a deliberate part of the room rather than a component that failed to load
 * (FRONTEND_SPEC §40).
 */
export function EmptyState({ title, body, children }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <span className="empty-state-mark" aria-hidden="true" />
      <p className="empty-state-title">{title}</p>
      <p className="empty-state-body">{body}</p>
      {children}
    </div>
  );
}
