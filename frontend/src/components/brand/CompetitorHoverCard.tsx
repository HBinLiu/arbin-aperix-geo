import { useLayoutEffect, useRef, useState } from "react";
import { Pencil, Trash2 } from "lucide-react";

import { BrandRankLabel } from "@/components/brand/BrandRankLabel";
import { SentimentValue } from "@/components/analysis/sentiment/SentimentValue";
import { FaviconImage } from "@/components/common/FaviconImage";
import { performanceTableClasses } from "@/components/analysis/prompt/performanceTableLayout";
import { DotBadge, TextBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useBrandGeoMetrics } from "@/hooks/useBrandGeoMetrics";
import type { BrandGeoMetrics } from "@/lib/brand/geoMetrics";
import { brandFaviconUrl, brandListIcon, brandWebsiteUrl } from "@/lib/brand/display";
import { brandRowLabel } from "@/lib/brand/hoverRow";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import type { CompetitorItem } from "@/types";

/** 竞品列表最小宽度（窄屏横向滚动） */
export const COMPETITOR_TABLE_MIN_WIDTH = 480;

/** 操作列固定宽度 */
export const COMPETITOR_ACTION_COL_WIDTH = "8.5rem";

type CompetitorHoverCardProps = {
  row: CompetitorItem;
  /** 页面已有 rank 行数据时可传入，跳过重复解析 */
  geoMetrics?: BrandGeoMetrics;
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
      <p className={cn("text-sm font-semibold tracking-tight tabular-nums", valueClassName)}>
        {value}
      </p>
    </div>
  );
}

function SentimentMetric({
  score,
  label,
}: {
  score: string | null;
  label: string | null;
}) {
  const hasScore = score != null && score !== "-";

  return (
    <div className="min-w-0 space-y-1">
      <p className="text-muted-foreground text-xs">情感倾向</p>
      {hasScore ? (
        <SentimentValue value={score} label={label} />
      ) : (
        <p className="text-sm font-semibold tracking-tight tabular-nums">—</p>
      )}
    </div>
  );
}

function GeoMetricsSkeleton() {
  return (
    <>
      {Array.from({ length: 4 }).map((_, index) => (
        <div key={index} className="min-w-0 space-y-1">
          <Skeleton className="h-3 w-10" />
          <Skeleton className="h-4 w-12" />
        </div>
      ))}
    </>
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
  return brandWebsiteUrl(row);
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
        <span className="absolute right-2 bottom-0 inline-flex items-baseline bg-gradient-to-l from-surface from-50% to-transparent pl-4">
          <button type="button" className={toggleButtonClass} onClick={() => setExpanded(true)}>
            展开
          </button>
        </span>
      ) : null}
    </div>
  );
}

/** 竞争对手悬停信息卡：简介 + 当前筛选下 GEO 四指标。 */
export function CompetitorHoverCard({ row, geoMetrics, className }: CompetitorHoverCardProps) {
  const label = brandRowLabel(row);
  const domain = row.domain.trim();
  const websiteUrl = competitorWebsiteUrl(row);
  const faviconUrl = brandFaviconUrl(row);
  const description = row.summary.trim() || "暂无简介。";
  const { metrics, isLoading } = useBrandGeoMetrics(row, geoMetrics);

  return (
    <div
      className={cn(
        "border-border w-[22rem] rounded-xl border bg-muted-background p-4 shadow-lg sm:w-[26rem]",
        className,
      )}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="flex items-center gap-3">
        {faviconUrl ? (
          <div className="border-border flex size-12 shrink-0 items-center justify-center rounded-md border bg-muted-background p-2">
            <FaviconImage
              url={faviconUrl}
              size={32}
              className="size-8 rounded-md"
              iconClassName="size-5"
              fallbackLabel={label}
            />
          </div>
        ) : (
          <div className="bg-background flex size-12 shrink-0 items-center justify-center rounded-full text-base font-semibold">
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
        <div
          className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4"
          aria-busy={isLoading}
        >
          {isLoading ? (
            <GeoMetricsSkeleton />
          ) : (
            <>
              <Metric label="可见度" value={metrics.visibility} />
              <Metric label="引用率" value={metrics.citationRate} />
              <Metric label="声量份额" value={metrics.shareVoice} />
              <SentimentMetric score={metrics.sentimentScore} label={metrics.sentimentLabel} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

type CompetitorTableRowProps = {
  row: CompetitorItem;
  onEdit: () => void;
  onRemove: () => void;
  actionDisabled?: boolean;
};

function competitorBrandIcon(row: CompetitorItem) {
  const faviconUrl = brandFaviconUrl(row);
  if (!faviconUrl) return brandListIcon(brandRowLabel(row), row.domain);
  return (
    <FaviconImage
      url={faviconUrl}
      size={20}
      className="size-5 shrink-0 rounded-md"
      fallbackLabel={brandRowLabel(row)}
    />
  );
}

export function CompetitorTableRow({ row, onEdit, onRemove, actionDisabled }: CompetitorTableRowProps) {
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
        <div className="flex gap-1">
          <Button
            type="button"
            variant="outline"
            size="icon"
            className={cn(
              "size-8 shrink-0 text-foreground hover:text-foreground",
              actionDisabled && "pointer-events-none opacity-50",
            )}
            aria-label="编辑"
            onClick={onEdit}
          >
            <Pencil className="size-4 stroke-[1.5]" aria-hidden />
          </Button>
          <Button
            type="button"
            variant="outline"
            size="icon"
            className={cn(
              "size-8 shrink-0 text-foreground hover:text-foreground",
              actionDisabled && "pointer-events-none opacity-50",
            )}
            aria-label="删除"
            onClick={onRemove}
          >
            <Trash2 className="size-4 stroke-[1.5]" aria-hidden />
          </Button>
        </div>
      </td>
    </tr>
  );
}
