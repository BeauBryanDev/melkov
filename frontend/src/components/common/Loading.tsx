import { Spinner } from "./Spinner";

interface LoadingProps {
  label?: string;
}

export function Loading({ label = "Loading" }: LoadingProps) {
  return (
    <div className="loading">
      <Spinner />
      <span>{label}</span>
    </div>
  );
}
