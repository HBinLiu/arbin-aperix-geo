import { useCallback, useLayoutEffect, useRef, useState, type ReactNode, type RefObject } from "react";
import { createPortal } from "react-dom";

import { cn } from "@/lib/utils";

const HOVER_CARD_GAP = 4;
const VIEWPORT_BOTTOM_PAD = 10;

function useHoverCardPosition(
  open: boolean,
  anchorRef: RefObject<HTMLDivElement | null>,
  cardRef: RefObject<HTMLDivElement | null>,
) {
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null);

  useLayoutEffect(() => {
    if (!open) {
      setPosition(null);
      return;
    }

    const update = () => {
      const anchor = anchorRef.current;
      const card = cardRef.current;
      if (!anchor || !card) return;

      const anchorRect = anchor.getBoundingClientRect();
      const cardHeight = card.offsetHeight;
      const cardWidth = card.offsetWidth;
      const viewportH = window.innerHeight;
      const viewportW = window.innerWidth;

      const labelHeight = anchorRect.height;
      let left = anchorRect.right + HOVER_CARD_GAP;
      let top = anchorRect.bottom + HOVER_CARD_GAP - labelHeight;

      if (top + cardHeight > viewportH - VIEWPORT_BOTTOM_PAD) {
        top = Math.max(VIEWPORT_BOTTOM_PAD, viewportH - cardHeight - VIEWPORT_BOTTOM_PAD);
      }

      if (left + cardWidth > viewportW - 8) {
        left = Math.max(8, anchorRect.left - HOVER_CARD_GAP - cardWidth);
      }

      setPosition({ top, left });
    };

    update();

    const cardEl = cardRef.current;
    const resizeObserver = cardEl ? new ResizeObserver(update) : null;
    if (cardEl && resizeObserver) {
      resizeObserver.observe(cardEl);
    }

    window.addEventListener("scroll", update, true);
    window.addEventListener("resize", update);
    return () => {
      resizeObserver?.disconnect();
      window.removeEventListener("scroll", update, true);
      window.removeEventListener("resize", update);
    };
  }, [open, anchorRef, cardRef]);

  return position;
}

type LabelHoverPortalProps = {
  label: string;
  content: ReactNode;
  /** 自定义悬停锚点；默认渲染可截断品牌名 */
  trigger?: ReactNode;
  className?: string;
  labelClassName?: string;
  contentClassName?: string;
};

/** 品牌名悬停锚点：标签可截断，悬停时在 portal 中展示详情卡。 */
export function LabelHoverPortal({
  label,
  content,
  trigger,
  className,
  labelClassName,
  contentClassName,
}: LabelHoverPortalProps) {
  const [hoverOpen, setHoverOpen] = useState(false);
  const labelRef = useRef<HTMLDivElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const closeTimerRef = useRef<number | null>(null);
  const cardPosition = useHoverCardPosition(hoverOpen, labelRef, cardRef);

  const openHover = useCallback(() => {
    if (closeTimerRef.current !== null) {
      window.clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
    setHoverOpen(true);
  }, []);

  const scheduleCloseHover = useCallback(() => {
    closeTimerRef.current = window.setTimeout(() => setHoverOpen(false), 80);
  }, []);

  return (
    <>
      <div
        ref={labelRef}
        className={cn("min-w-0", className)}
        onMouseEnter={openHover}
        onMouseLeave={scheduleCloseHover}
      >
        {trigger ?? (
          <p
            className={cn(
              "truncate text-sm font-medium transition-colors",
              hoverOpen && "text-primary underline underline-offset-2",
              labelClassName,
            )}
          >
            {label}
          </p>
        )}
      </div>
      {hoverOpen
        ? createPortal(
            <div
              ref={cardRef}
              className={cn("fixed z-50", !cardPosition && "pointer-events-none opacity-0")}
              style={
                cardPosition
                  ? { top: cardPosition.top, left: cardPosition.left }
                  : { top: 0, left: 0 }
              }
              onMouseEnter={openHover}
              onMouseLeave={scheduleCloseHover}
            >
              <div className={contentClassName}>{content}</div>
            </div>,
            document.body,
          )
        : null}
    </>
  );
}
