import { type ReactNode, useEffect, useMemo } from "react";
import { type LucideIcon } from "lucide-react";

import { BrandRankIcon } from "@/components/analysis/common/BrandRankIcon";
import { DateRangeFilterSelect } from "@/components/analysis/common/DateRangeFilterSelect";
import { PlatformFilterSelect } from "@/components/analysis/common/PlatformFilterSelect";
import { TopicFilterSelect } from "@/components/analysis/common/TopicFilterSelect";
import { TextBadge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from "@/components/ui/select";
import { useAnalysisFilter } from "@/hooks/useAnalysisFilter";
import { ANALYSIS_ENTITY_OWN } from "@/lib/analysis";
import {
  faviconCandidateUrls,
  faviconUrlFromHost,
  getFaviconClientStatus,
  markFaviconClientOk,
} from "@/lib/favicon";
import type { AnalysisEntityRef, AnalysisFilters } from "@/types";
import { cn } from "@/lib/utils";

export type FilterSelectProps = {
  icon?: LucideIcon;
  /** 自定义触发器左侧内容（如品牌 favicon），优先于 icon */
  leading?: ReactNode;
  value: string;
  displayValue?: string;
  placeholder: string;
  disabled?: boolean;
  title?: string;
  onValueChange?: (value: string) => void;
  children?: ReactNode;
  className?: string;
  contentClassName?: string;
  variant?: "default" | "primary";
};

function EntityFilterOption({ entity }: { entity: AnalysisEntityRef }) {
  const isOwn = entity.kind === "own" || entity.id === ANALYSIS_ENTITY_OWN;

  return (
    <span className="flex min-w-0 flex-1 items-center gap-2">
      <BrandRankIcon label={entity.label} size="sm" faviconLoadingSpinner={false} />
      <span className="min-w-0 flex-1 truncate">{entity.display_name}</span>
      {isOwn ? (
        <TextBadge variant="primary" className="shrink-0 px-2 py-0.5 text-xs font-semibold">
          拥有
        </TextBadge>
      ) : null}
    </span>
  );
}

export function FilterSelect({
  icon: Icon,
  leading,
  value,
  displayValue,
  placeholder,
  disabled,
  title,
  onValueChange,
  children,
  className,
  contentClassName,
  variant = "default",
}: FilterSelectProps) {
  const isPrimary = variant === "primary";

  return (
    <Select value={value} onValueChange={onValueChange} disabled={disabled}>
      <SelectTrigger
        title={title}
        className={cn(
          "h-9 w-auto gap-2 rounded-lg px-3 text-xs font-normal",
          isPrimary && [
            "border-primary bg-primary text-primary-foreground",
            "hover:border-primary hover:bg-primary",
            "focus:border-primary focus-visible:border-primary",
            "data-[state=open]:border-primary",
            "[&>svg:last-child]:size-4 [&>svg:last-child]:stroke-[2.5] [&>svg:last-child]:text-primary-foreground [&>svg:last-child]:opacity-100",
          ],
          disabled && "opacity-60",
          className,
        )}
      >
        {leading ??
          (Icon ? (
            <Icon
              className={cn("size-3.5 shrink-0", isPrimary ? "text-primary-foreground" : "text-muted-foreground")}
              aria-hidden
            />
          ) : null)}
        <span className={cn("truncate", isPrimary ? "font-medium text-primary-foreground" : "text-foreground")}>
          {displayValue ?? placeholder}
        </span>
      </SelectTrigger>
      {children ? <SelectContent className={contentClassName}>{children}</SelectContent> : null}
    </Select>
  );
}

export type AnalysisFilterBarProps = {
  value: AnalysisFilters;
  onChange: React.Dispatch<React.SetStateAction<AnalysisFilters>>;
  /** 紧挨筛选条件之后（如提示词搜索框） */
  afterFilters?: ReactNode;
  /** 居右显示（如管理提示词按钮） */
  trailing?: ReactNode;
  /** 对比页（排行榜）可隐藏实体切换 */
  hideEntityFilter?: boolean;
  /** 隐藏平台筛选（少数页面不需要按平台过滤） */
  hidePlatformFilter?: boolean;
  /** 提示词详情页已固定单条提示词，隐藏主题筛选 */
  hideTopicFilter?: boolean;
};

/** 分析页筛选条：分析对象、时间、主题、平台。 */
export function AnalysisFilterBar({
  value,
  onChange,
  afterFilters,
  trailing,
  hideEntityFilter = false,
  hidePlatformFilter = false,
  hideTopicFilter = false,
}: AnalysisFilterBarProps) {
  const { entities, topics, platforms } = useAnalysisFilter();

  const { from, to, entityId, platformIds, topicIds } = value;
  const selectedEntity = entities.find((entity) => entity.id === (entityId || ANALYSIS_ENTITY_OWN));
  const ownEntity = entities.find((entity) => entity.id === ANALYSIS_ENTITY_OWN);
  const entityIconLabel = selectedEntity?.label ?? ownEntity?.label ?? null;

  useEffect(() => {
    if (!entityIconLabel) return;
    const pageUrl = faviconUrlFromHost(entityIconLabel);
    if (!pageUrl || getFaviconClientStatus(pageUrl) === "ok") return;
    const src = faviconCandidateUrls(pageUrl)[0];
    if (!src) return;
    const img = new Image();
    img.src = src;
    img.onload = () => markFaviconClientOk(pageUrl);
  }, [entityIconLabel]);

  const entityLeading = useMemo(
    () => <BrandRankIcon label={entityIconLabel} size="sm" faviconLoadingSpinner={false} />,
    [entityIconLabel],
  );

  return (
    <div className="sticky top-0 z-20 flex w-full max-w-full min-w-0 flex-wrap items-center gap-2 border-b bg-muted-background px-4 py-3">
      {!hideEntityFilter ? (
        <FilterSelect
          variant="primary"
          leading={entityLeading}
          value={entityId || ANALYSIS_ENTITY_OWN}
          displayValue={selectedEntity?.display_name ?? "所有品牌"}
          placeholder="分析对象"
          contentClassName="min-w-[14rem]"
          onValueChange={(id) => onChange((prev) => ({ ...prev, entityId: id }))}
          disabled={entities.length === 0}
        >
          {entities.map((entity) => (
            <SelectItem key={entity.id} value={entity.id}>
              <EntityFilterOption entity={entity} />
            </SelectItem>
          ))}
        </FilterSelect>
      ) : null}

      <DateRangeFilterSelect
        from={from}
        to={to}
        onChange={(range) => onChange((prev) => ({ ...prev, ...range }))}
      />

      {!hidePlatformFilter ? (
        <PlatformFilterSelect
          platforms={platforms}
          value={platformIds}
          onChange={(ids) => onChange((prev) => ({ ...prev, platformIds: ids }))}
          disabled={platforms.length === 0}
        />
      ) : null}

      {!hideTopicFilter ? (
        <TopicFilterSelect
          topics={topics}
          value={topicIds}
          onChange={(ids) => onChange((prev) => ({ ...prev, topicIds: ids }))}
          disabled={topics.length === 0}
        />
      ) : null}

      {afterFilters}

      {trailing ? (
        <div className="ml-auto flex min-w-0 shrink-0 flex-wrap items-center gap-2">{trailing}</div>
      ) : null}
    </div>
  );
}
