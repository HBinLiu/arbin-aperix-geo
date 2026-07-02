import { BrandRankIcon, type BrandRankIconShape, type BrandRankIconSize } from "@/components/analysis/common/BrandRankIcon";
import { CompetitorHoverCard } from "@/components/brand/CompetitorHoverCard";
import { LabelHoverPortal } from "@/components/brand/LabelHoverPortal";
import { TextBadge } from "@/components/ui/badge";
import { useBrandHoverRow } from "@/hooks/useBrandHoverRow";
import { brandIconFaviconLabel } from "@/lib/brand/iconColor";
import { brandRowLabel } from "@/lib/brand/hoverRow";
import type { BrandGeoMetrics } from "@/lib/brand/geoMetrics";
import { cn } from "@/lib/utils";
import type { CompetitorItem } from "@/types";

type BrandRankLabelProps = {
  label: string;
  icon?: React.ReactNode;
  size?: BrandRankIconSize;
  shape?: BrandRankIconShape;
  /** 自有品牌 */
  isOwn?: boolean;
  /** FilterBar 当前分析对象（非自有） */
  isFocus?: boolean;
  /** 已知竞品行时直接传入，否则按 label + 主体解析 */
  hoverRow?: CompetitorItem;
  /** 列表已有 domain 时传入，保证悬停卡 favicon 与列表一致 */
  domain?: string | null;
  /** 悬停展示详情卡，默认 true */
  showHover?: boolean;
  /** 页面已有 rank 行数据时可传入，悬停卡直接展示 */
  geoMetrics?: BrandGeoMetrics;
  className?: string;
};

const HOVER_CARD_ANIMATION =
  "animate-in fade-in-0 zoom-in-95 slide-in-from-left-2 duration-200";

/** 排名/列表品牌列：图标 + 可截断名称 + 悬停详情卡 + 可选徽章。 */
export function BrandRankLabel({
  label,
  icon,
  size = "default",
  shape = "square",
  isOwn,
  isFocus,
  hoverRow,
  domain,
  showHover = true,
  geoMetrics,
  className,
}: BrandRankLabelProps) {
  const resolvedHoverRow = useBrandHoverRow(label, hoverRow, domain);
  const displayLabel = brandRowLabel(resolvedHoverRow) || label.trim();
  const faviconLabel = brandIconFaviconLabel(displayLabel, domain ?? resolvedHoverRow.domain);

  return (
    <div className={cn("flex min-w-0 w-full items-center gap-2", className)}>
      {icon ?? <BrandRankIcon label={faviconLabel} size={size} shape={shape} />}
      {showHover ? (
        <LabelHoverPortal
          label={displayLabel}
          content={<CompetitorHoverCard row={resolvedHoverRow} geoMetrics={geoMetrics} />}
          contentClassName={HOVER_CARD_ANIMATION}
        />
      ) : (
        <p className="truncate text-sm font-medium">{displayLabel}</p>
      )}
      {isOwn ? (
        <TextBadge variant="primary" className="shrink-0">
          拥有
        </TextBadge>
      ) : null}
      {isFocus && !isOwn ? (
        <TextBadge variant="gray" className="shrink-0">
          当前
        </TextBadge>
      ) : null}
    </div>
  );
}
