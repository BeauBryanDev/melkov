import { useEffect, useRef } from "react";

/**
 * Keep a scroll container pinned to its newest content.
 *
 */
export function useAutoScroll<T>(dependency: T) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node) {
      return;
    }
    node.scrollTo({ top: node.scrollHeight, behavior: "smooth" });
  }, [dependency]);

  return ref;
}
