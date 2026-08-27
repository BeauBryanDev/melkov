interface SpinnerProps {
  className?: string;
}

export function Spinner({ className }: SpinnerProps) {
  return <span className={className ?? "spinner"} aria-hidden="true" />;
}
