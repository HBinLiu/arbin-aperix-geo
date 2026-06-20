import { useLayoutEffect, useRef, useState } from "react";
import { Trash2 } from "lucide-react";

import { BrandRankLabel } from "@/components/brand/BrandRankLabel";
import { FaviconImage } from "@/components/common/FaviconImage";
import { performanceTableClasses } from "@/components/analysis/prompt/performanceTableLayout";
import { DotBadge, TextBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { brandRowLabel } from "@/lib/brand/hoverRow";
import { faviconUrlFromHost, faviconUrlFromWebsite } from "@/lib/favicon";
import { cn } from "@/lib/utils";
import type { CompetitorItem } from "@/types";

/** 竞品列表最小宽度（窄屏横向滚动） */
export const COMPETITOR_TABLE_MIN_WIDTH = 480;

/** 操作列固定宽度 */
export const COMPETITOR_ACTION_COL_WIDTH = "6rem";

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
    <TextBadge
      variant="gray"
      className="rounded bg-violet-100 px-1.5 py-0.5 text-[10px] font-semibold tracking-wide text-violet-700"
    >
      {children}
    </TextBadge>
  );
}

function competitorWebsiteUrl(row: CompetitorItem): string | null {
  const url = row.website_url?.trim();
  if (url) return url;
  const domain = row.domain?.trim();
  if (domain) return faviconUrlFromHost(domain);
  return null;
}

/** 简介：两行截断，展开/收起按钮紧贴正文末尾。 */
function CollapsibleDescription({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false);
  const [canToggle, setCanToggle] = useState(false);
  const descriptionRef = useRef<HTMLParagraphElement>(null);

  useLayoutEffect(() => {
    setExpanded(false);
  }, [text]);

  useLayoutEffect(() => {
    if (expanded) return;

    const el = descriptionRef.current;
    if (!el) return;

    const checkOverflow = () => {
      setCanToggle(el.scrollHeight > el.clientHeight + 1);
    };

    checkOverflow();
    const observer = new ResizeObserver(checkOverflow);
    observer.observe(el);
    return () => observer.disconnect();
  }, [text, expanded]);

  const toggleButtonClass =
    "text-primary inline align-baseline text-xs font-medium leading-relaxed hover:underline";

  return (
    <div className="relative mt-2">
      <p
        ref={descriptionRef}
        className={cn(
          "text-muted-foreground text-xs leading-relaxed",
          !expanded && "line-clamp-2",
        )}
      >
        {text}
        {!expanded && canToggle ? (
          <span aria-hidden className="float-right ml-1 h-[1.625em] w-10 shrink-0 clear-both" />
        ) : null}
        {expanded && canToggle ? (
          <>
            {" "}
            <button type="button" className={toggleButtonClass} onClick={() => setExpanded(false)}>
              收起
            </button>
          </>
        ) : null}
      </p>
      {!expanded && canToggle ? (
        <span className="absolute right-2 bottom-0 inline-flex items-baseline bg-gradient-to-l from-white from-50% to-transparent pl-4">
          <button type="button" className={toggleButtonClass} onClick={() => setExpanded(true)}>
            展开
          </button>
        </span>
      ) : null}
    </div>
  );
}

/** 竞争对手悬停信息卡（GEO 指标待后端接入）。 */
export function CompetitorHoverCard({ row, className }: CompetitorHoverCardProps) {
  const label = brandRowLabel(row);
  const domain = row.domain.trim();
  const websiteUrl = competitorWebsiteUrl(row);
  const faviconUrl = faviconUrlFromWebsite(row.website_url, domain);
  const description = row.summary.trim() || "暂无简介。";

  return (
    <div
      className={cn(
        "border-border w-[22rem] rounded-xl border bg-white p-4 shadow-lg sm:w-[26rem]",
        className,
      )}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="flex items-center gap-3">
        {faviconUrl ? (
          <div className="border-border flex size-12 shrink-0 items-center justify-center rounded-md border bg-white p-2">
            <FaviconImage url={faviconUrl} size={32} className="size-8" iconClassName="size-5" />
          </div>
        ) : (
          <div className="bg-muted flex size-12 shrink-0 items-center justify-center rounded-full text-base font-semibold">
            {label.slice(0, 1)}
          </div>
        )}
        <div className="min-w-0 flex-1">
          <p className="truncate text-base font-semibold tracking-tight">{label}</p>
          {domain ? (
            websiteUrl ? (
              <a
                href={websiteUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted-foreground block truncate text-sm hover:underline"
                onClick={(e) => e.stopPropagation()}
              >
                {domain}
              </a>
            ) : (
              <p className="text-muted-foreground truncate text-sm">{domain}</p>
            )
          ) : null}
        </div>
      </div>

      <CollapsibleDescription text={description} />

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

function competitorBrandIcon(row: CompetitorItem) {
  const faviconUrl = faviconUrlFromWebsite(row.website_url, row.domain);
  if (!faviconUrl) return undefined;
  return <FaviconImage url={faviconUrl} size={20} className="size-5 shrink-0 rounded-md" />;
}

export function CompetitorTableRow({ row, onRemove, removeDisabled }: CompetitorTableRowProps) {
  const label = brandRowLabel(row);

  return (
    <tr className={cn(performanceTableClasses.row, "relative")}>
      <td className="min-w-0 max-w-0 overflow-hidden">
        <BrandRankLabel
          label={label}
          icon={competitorBrandIcon(row)}
          size="sm"
          hoverRow={row}
        />
      </td>

      <td>
        <DotBadge variant="success" className="gap-1.5 px-1.5 py-0.5 font-medium">
          就绪
        </DotBadge>
      </td>

      <td>
        <Button
          type="button"
          variant="outline"
          size="icon"
          className={cn(
            "size-8 shrink-0 text-foreground hover:text-foreground",
            removeDisabled && "pointer-events-none opacity-50",
          )}
          aria-label="删除"
          onClick={onRemove}
        >
          <Trash2 className="size-4 stroke-[1.5]" aria-hidden />
        </Button>
      </td>
    </tr>
  );
}
