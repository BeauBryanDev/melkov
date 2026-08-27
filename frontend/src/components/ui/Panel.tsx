import type { HTMLAttributes, ReactNode } from "react";
import clsx from "clsx";
import { PanelCorners } from "./Ornaments";

interface PanelProps extends HTMLAttributes<HTMLElement> {
  children: ReactNode;
}

export function Panel({ className, children, ...props }: PanelProps) {
  return (
    <section className={clsx("panel", className)} {...props}>
      <PanelCorners />
      {children}
    </section>
  );
}

