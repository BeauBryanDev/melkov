import brush1 from "../../assets/painting_brush1.svg";
import brush2 from "../../assets/painting_brush2.svg";

interface BrushAnimationProps {
  className?: string;
}

export function BrushAnimation({ className }: BrushAnimationProps) {
  return (
    <div className={className ?? "brush-animation"} aria-hidden="true">
      <img src={brush1} alt="" />
      <img src={brush2} alt="" />
    </div>
  );
}
