import { useEffect, useState } from "react";

/** 全局鼠标坐标，供眼动头像等组件共享一次 mousemove 监听。 */
export function useMousePosition(enabled = true) {
  const [position, setPosition] = useState({ x: 0, y: 0 });

  useEffect(() => {
    if (!enabled) return;

    const onMouseMove = (event: MouseEvent) => {
      setPosition({ x: event.clientX, y: event.clientY });
    };

    window.addEventListener("mousemove", onMouseMove, { passive: true });
    return () => window.removeEventListener("mousemove", onMouseMove);
  }, [enabled]);

  return position;
}
