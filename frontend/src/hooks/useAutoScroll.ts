import { useEffect, useRef } from "react";

/**
 * Keep a scroll container pinned to its newest content.
 *
 * The container is scrolled directly rather than calling `scrollIntoView` on
 * a sentinel: that method scrolls every ancestor, which drags the whole page
 * down when a long reply lands.
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
