import type { ButtonHTMLAttributes, ReactNode } from "react";
import clsx from "clsx";

interface RoyalButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  tone?: "primary" | "secondary";
  loading?: boolean;
}

/**
 * The atelier's button.
 *
 * `loading` disables the control as well as marking it, so a slow turn cannot
 * be sent twice by an impatient second click.
 */
export function RoyalButton({
  className,
  children,
  tone = "primary",
  loading = false,
  disabled,
  ...props
}: RoyalButtonProps) {
  return (
    <button
      className={clsx("royal-button", `royal-button-${tone}`, className)}
      data-loading={loading || undefined}
      disabled={disabled || loading}
      {...props}
    >
      {children}
    </button>
  );
}
