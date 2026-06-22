import { BrandRankIcon } from "@/components/analysis/common/BrandRankIcon";
import { CompetitorHoverCard } from "@/components/brand/CompetitorHoverCard";
import { LabelHoverPortal } from "@/components/brand/LabelHoverPortal";
import { TextBadge } from "@/components/ui/badge";
import { useBrandHoverRow } from "@/hooks/useBrandHoverRow";
import type { BrandGeoMetrics } from "@/lib/brand/geoMetrics";
import { cn } from "@/lib/utils";
import type { CompetitorItem } from "@/types";

type BrandRankIconSize = "sm" | "default" | "lg";
type BrandRankIconShape = "square" | "circle";

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
  showHover = true,
  geoMetrics,
  className,
}: BrandRankLabelProps) {
  const resolvedHoverRow = useBrandHoverRow(label, hoverRow);

  return (
    <div className={cn("flex min-w-0 w-full items-center gap-2", className)}>
      {icon ?? <BrandRankIcon label={label} size={size} shape={shape} />}
      {showHover ? (
        <LabelHoverPortal
          label={label}
          content={<CompetitorHoverCard row={resolvedHoverRow} geoMetrics={geoMetrics} />}
          contentClassName={HOVER_CARD_ANIMATION}
        />
      ) : (
        <p className="truncate text-sm font-medium">{label}</p>
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
