import { useRef } from "react";

import { cn } from "@/lib/utils";

export function pupilOffsetFromMouse(
  anchor: DOMRect,
  mouseX: number,
  mouseY: number,
  maxDistance: number,
  forced?: { x: number; y: number },
) {
  if (forced) return forced;

  const centerX = anchor.left + anchor.width / 2;
  const centerY = anchor.top + anchor.height / 2;
  const deltaX = mouseX - centerX;
  const deltaY = mouseY - centerY;
  const distance = Math.min(Math.hypot(deltaX, deltaY), maxDistance);
  const angle = Math.atan2(deltaY, deltaX);

  return {
    x: Math.cos(angle) * distance,
    y: Math.sin(angle) * distance,
  };
}

type EyeBallProps = {
  size: number;
  pupilSize: number;
  maxDistance: number;
  mouseX: number;
  mouseY: number;
  isBlinking?: boolean;
  animate?: boolean;
  className?: string;
};

/** 单眼：瞳孔跟随鼠标（逻辑参考 CareerCompass animated-characters）。 */
export function EyeBall({
  size,
  pupilSize,
  maxDistance,
  mouseX,
  mouseY,
  isBlinking = false,
  animate = true,
  className,
}: EyeBallProps) {
  const eyeRef = useRef<HTMLDivElement>(null);
  const anchor = eyeRef.current?.getBoundingClientRect();
  const pupilOffset =
    animate && anchor
      ? pupilOffsetFromMouse(anchor, mouseX, mouseY, maxDistance)
      : { x: 0, y: 0 };

  return (
    <div
      ref={eyeRef}
      className={cn("relative shrink-0", className)}
      style={{ width: size, height: size }}
      aria-hidden
    >
      <div
        className="absolute inset-0 overflow-hidden rounded-full bg-white"
        style={{
          transform: isBlinking ? "scaleY(0.12)" : "scaleY(1)",
          transformOrigin: "center",
          transition: "transform 120ms ease-out",
        }}
      >
        <div className="flex size-full items-center justify-center">
          <div
            className="rounded-full bg-[#2d2d2d]"
            style={{
              width: pupilSize,
              height: pupilSize,
              opacity: isBlinking ? 0 : 1,
              transform: `translate(${pupilOffset.x}px, ${pupilOffset.y}px)`,
              transition: animate ? "transform 100ms ease-out, opacity 80ms ease-out" : undefined,
            }}
          />
        </div>
      </div>
    </div>
  );
}
