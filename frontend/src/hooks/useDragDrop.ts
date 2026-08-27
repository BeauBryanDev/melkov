import { useCallback, useState } from "react";
import type { DragEvent } from "react";

interface UseDragDropOptions {
  onFile: (file: File) => void;
  disabled?: boolean;
}

/**
 * Drag-and-drop handlers for the frame.
 *
 * `dragCounter` exists because `dragenter`/`dragleave` fire for every nested
 * element the pointer crosses; counting them keeps the gold drag highlight
 * from flickering as the pointer moves over the frame's inner ornaments.
 */
export function useDragDrop({ onFile, disabled = false }: UseDragDropOptions) {
  const [isDragging, setIsDragging] = useState(false);
  const [depth, setDepth] = useState(0);

  const onDragEnter = useCallback(
    (event: DragEvent<HTMLElement>) => {
      event.preventDefault();
      if (disabled) return;
      setDepth((value) => {
        if (value === 0) setIsDragging(true);
        return value + 1;
      });
    },
    [disabled],
  );

  const onDragLeave = useCallback((event: DragEvent<HTMLElement>) => {
    event.preventDefault();
    setDepth((value) => {
      const next = Math.max(0, value - 1);
      if (next === 0) setIsDragging(false);
      return next;
    });
  }, []);

  const onDragOver = useCallback((event: DragEvent<HTMLElement>) => {
    event.preventDefault();
  }, []);

  const onDrop = useCallback(
    (event: DragEvent<HTMLElement>) => {
      event.preventDefault();
      setDepth(0);
      setIsDragging(false);
      if (disabled) return;

      const file = event.dataTransfer.files?.[0];
      if (file) {
        onFile(file);
      }
    },
    [disabled, onFile],
  );

  return {
    isDragging,
    dragHandlers: { onDragEnter, onDragLeave, onDragOver, onDrop },
  };
}
