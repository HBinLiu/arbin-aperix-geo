import { useCallback, useLayoutEffect, useRef, useState, type RefObject } from "react";
import { createPortal } from "react-dom";
import { Trash2 } from "lucide-react";

import { FaviconImage } from "@/components/common/FaviconImage";
import { cn } from "@/lib/utils";
import type { CompetitorItem } from "@/types";

type CompetitorHoverCardProps = {
  row: CompetitorItem;
  className?: string;
};

type MetricProps = {
  label: string;
  value: string;
  valueClassName?: string;
};

function Metric({ label, value, valueClassName }: MetricProps) {
  return (
    <div className="min-w-0 space-y-1">
      <p className="text-muted-foreground text-xs">{label}</p>
      <p className={cn("text-sm font-semibold tracking-tight", valueClassName)}>{value}</p>
    </div>
  );
}

function SectionBadge({ children }: { children: string }) {
  return (
    <span className="inline-flex rounded bg-violet-100 px-1.5 py-0.5 text-[10px] font-semibold tracking-wide text-violet-700">
      {children}
    </span>
  );
}

function rowLabel(row: CompetitorItem): string {
  return row.brand.trim() || row.domain;
}

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

      if (top + cardHeight > viewportH) {
        top = Math.max(0, viewportH - cardHeight - VIEWPORT_BOTTOM_PAD);
      }

      if (left + cardWidth > viewportW - 8) {
        left = Math.max(8, anchorRect.left - HOVER_CARD_GAP - cardWidth);
      }

      setPosition({ top, left });
    };

    update();
    window.addEventListener("scroll", update, true);
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update, true);
      window.removeEventListener("resize", update);
    };
  }, [open, anchorRef, cardRef]);

  return position;
}

/** 竞争对手悬停信息卡（GEO 指标待后端接入）。 */
export function CompetitorHoverCard({ row, className }: CompetitorHoverCardProps) {
  const [expanded, setExpanded] = useState(false);
  const label = rowLabel(row);
  const domain = row.domain.trim();
  const description = row.summary.trim() || "暂无简介。";
  const canExpand = description.length > 72;

  return (
    <div
      className={cn(
        "border-border w-[22rem] rounded-xl border bg-white p-4 shadow-lg sm:w-[26rem]",
        className,
      )}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="flex items-center gap-3">
        {domain ? (
          <div className="border-border flex size-12 shrink-0 items-center justify-center rounded-md border bg-white p-2">
            <FaviconImage domain={domain} size={32} className="size-8" iconClassName="size-5" />
          </div>
        ) : (
          <div className="bg-muted flex size-12 shrink-0 items-center justify-center rounded-full text-base font-semibold">
            {label.slice(0, 1)}
          </div>
        )}
        <div className="min-w-0 flex-1">
          <p className="truncate text-base font-semibold tracking-tight">{label}</p>
          {domain ? <p className="text-muted-foreground truncate text-sm">{domain}</p> : null}
        </div>
      </div>

      <p className={cn("text-muted-foreground mt-2 text-xs leading-relaxed", !expanded && "line-clamp-2")}>
        {description}
        {canExpand && !expanded ? (
          <button
            type="button"
            className="text-primary ml-1 inline font-medium hover:underline"
            onClick={() => setExpanded(true)}
          >
            展开
          </button>
        ) : null}
      </p>

      <div className="mt-2">
        <div className="flex items-center gap-2">
          <SectionBadge>GEO</SectionBadge>
          <div className="bg-border h-px min-w-0 flex-1" aria-hidden />
        </div>
        <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
          <Metric label="可见度" value="0%" />
          <Metric label="引用率" value="0%" />
          <Metric label="声量份额" value="—" />
          <Metric label="情感倾向" value="—" />
        </div>
      </div>
    </div>
  );
}

type CompetitorTableRowProps = {
  row: CompetitorItem;
  onRemove: () => void;
  removeDisabled?: boolean;
};

export function CompetitorTableRow({ row, onRemove, removeDisabled }: CompetitorTableRowProps) {
  const [hoverOpen, setHoverOpen] = useState(false);
  const labelRef = useRef<HTMLDivElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const closeTimerRef = useRef<number | null>(null);
  const label = rowLabel(row);
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
    <li className="relative grid grid-cols-[minmax(0,1fr)_6rem_4rem] items-center gap-2 px-3 py-2 sm:grid-cols-[minmax(0,1fr)_7rem_4rem]">
      <div className="flex min-w-0 items-center gap-2">
        {row.domain ? (
          <FaviconImage domain={row.domain} size={20} className="size-5 shrink-0" />
        ) : (
          <span className="bg-muted flex size-5 shrink-0 items-center justify-center rounded text-[10px] font-semibold">
            {row.brand.slice(0, 1)}
          </span>
        )}
        <div
          ref={labelRef}
          className="min-w-0"
          onMouseEnter={openHover}
          onMouseLeave={scheduleCloseHover}
        >
          <p
            className={cn(
              "truncate text-sm font-medium transition-colors",
              hoverOpen && "text-primary",
            )}
          >
            {label}
          </p>
        </div>
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
              <CompetitorHoverCard
                row={row}
                className="animate-in fade-in-0 zoom-in-95 slide-in-from-left-2 duration-200"
              />
            </div>,
            document.body,
          )
        : null}

      <span className="inline-flex items-center gap-1.5 text-xs text-emerald-600">
        <span className="size-1.5 rounded-full bg-emerald-500" aria-hidden />
        就绪
      </span>

      <div className="flex justify-end">
        <button
          type="button"
          className={cn(
            "text-muted-foreground hover:text-destructive rounded-md p-1.5 transition-colors",
            removeDisabled && "pointer-events-none opacity-50",
          )}
          aria-label="删除"
          onClick={onRemove}
        >
          <Trash2 className="size-4" aria-hidden />
        </button>
      </div>
    </li>
  );
}
