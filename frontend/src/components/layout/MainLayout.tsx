import type { ReactNode } from "react";

interface MainLayoutProps {
  header: ReactNode;
  children: ReactNode;
  footer: ReactNode;
}

export function MainLayout({ header, children, footer }: MainLayoutProps) {
  return (
    <div className="app-shell">
      {header}
      {children}
      {footer}
    </div>
  );
}
