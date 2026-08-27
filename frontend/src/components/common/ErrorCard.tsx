import type { ReactNode } from "react";

interface ErrorCardProps {
  title?: string;
  message: string;
  action?: ReactNode;
}

export function ErrorCard({ title = "Something went wrong", message, action }: ErrorCardProps) {
  return (
    <div className="error-card">
      <strong>{title}</strong>
      <p>{message}</p>
      {action}
    </div>
  );
}
