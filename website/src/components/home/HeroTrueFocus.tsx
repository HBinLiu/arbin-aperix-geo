import React from "react";
import type { HeroHeadlinePart } from "@/lib/home";

type Props = {
  parts: HeroHeadlinePart[];
  blurAmount?: number;
  borderColor?: string;
  animationDuration?: number;
  pauseBetweenAnimations?: number;
};

type FocusRect = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export default function HeroTrueFocus({
  parts,
  blurAmount = 5,
  borderColor = "#ff6b2b",
  animationDuration = 0.5,
  pauseBetweenAnimations = 1,
}: Props) {
  const focusIndices = React.useMemo(
    () =>
      parts.reduce<number[]>((indices, part, index) => {
        if (part.type === "focus") indices.push(index);
        return indices;
      }, []),
    [parts],
  );

  const [activeFocusSlot, setActiveFocusSlot] = React.useState(0);
  const [focusRect, setFocusRect] = React.useState<FocusRect>({
    x: 0,
    y: 0,
    width: 0,
    height: 0,
  });
  const [ready, setReady] = React.useState(false);
  const [reduceMotion, setReduceMotion] = React.useState(false);

  const containerRef = React.useRef<HTMLSpanElement>(null);
  const wordRefs = React.useRef<(HTMLSpanElement | null)[]>([]);

  const activePartIndex = focusIndices[activeFocusSlot] ?? focusIndices[0] ?? -1;

  React.useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => setReduceMotion(media.matches);
    sync();
    media.addEventListener("change", sync);
    return () => media.removeEventListener("change", sync);
  }, []);

  React.useEffect(() => {
    if (reduceMotion || focusIndices.length <= 1) return;

    const interval = window.setInterval(
      () => {
        setActiveFocusSlot((prev) => (prev + 1) % focusIndices.length);
      },
      (animationDuration + pauseBetweenAnimations) * 1000,
    );

    return () => window.clearInterval(interval);
  }, [
    animationDuration,
    focusIndices.length,
    pauseBetweenAnimations,
    reduceMotion,
  ]);

  React.useLayoutEffect(() => {
    const container = containerRef.current;
    const activeEl = wordRefs.current[activePartIndex];
    if (!container || !activeEl || activePartIndex < 0) return;

    let cancelled = false;

    const updateRect = () => {
      if (cancelled) return;

      const parentRect = container.getBoundingClientRect();
      const activeRect = activeEl.getBoundingClientRect();
      const insetX = 3;
      const insetY = 3;

      setFocusRect({
        x: activeRect.left - parentRect.left + insetX,
        y: activeRect.top - parentRect.top + insetY,
        width: Math.max(0, activeRect.width - insetX * 2),
        height: Math.max(0, activeRect.height - insetY * 2),
      });
      setReady(true);
    };

    updateRect();

    const fontsReady = document.fonts?.ready;
    if (fontsReady) {
      void fontsReady.then(updateRect);
    }

    const observer = new ResizeObserver(updateRect);
    observer.observe(container);
    observer.observe(activeEl);
    window.addEventListener("resize", updateRect);

    return () => {
      cancelled = true;
      observer.disconnect();
      window.removeEventListener("resize", updateRect);
    };
  }, [activePartIndex, parts]);

  if (!parts.length) return null;

  return (
    <span ref={containerRef} className="hero-true-focus">
      {parts.map((part, index) => {
        if (part.type === "text") {
          return (
            <span key={`text-${index}`} className="hero-true-focus-text">
              {part.content}
            </span>
          );
        }

        const isActive = index === activePartIndex;
        const shouldAnimate = !reduceMotion && focusIndices.length > 1;
        const blur = shouldAnimate && !isActive ? blurAmount : 0;
        const opacity = shouldAnimate && !isActive ? 0.45 : 1;

        return (
          <span
            key={`focus-${index}`}
            ref={(el) => {
              wordRefs.current[index] = el;
            }}
            className="hero-true-focus-word"
            style={{
              filter: `blur(${blur}px)`,
              opacity,
              transition: shouldAnimate
                ? `filter ${animationDuration}s ease, opacity ${animationDuration}s ease`
                : undefined,
            }}
          >
            {part.content}
          </span>
        );
      })}

      {!reduceMotion && focusIndices.length > 0 && activePartIndex >= 0 && (
        <span
          className="hero-true-focus-bracket"
          aria-hidden="true"
          style={{
            transform: `translate(${focusRect.x}px, ${focusRect.y}px)`,
            width: focusRect.width,
            height: focusRect.height,
            opacity: ready && focusRect.width > 0 ? 1 : 0,
            transitionDuration: `${animationDuration}s`,
            ["--hero-focus-border" as string]: borderColor,
          }}
        >
          <span className="hero-true-focus-corner hero-true-focus-corner-tl" />
          <span className="hero-true-focus-corner hero-true-focus-corner-tr" />
          <span className="hero-true-focus-corner hero-true-focus-corner-bl" />
          <span className="hero-true-focus-corner hero-true-focus-corner-br" />
        </span>
      )}
    </span>
  );
}
