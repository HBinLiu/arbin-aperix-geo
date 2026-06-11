import { useMemo, type ReactNode } from "react";
import { Bot, Calendar, Hash, MapPin, Tag, type LucideIcon } from "lucide-react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from "@/components/ui/select";
import { useAnalysisFilter } from "@/hooks/useAnalysisFilter";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { ANALYSIS_DATE_OPTIONS, ANALYSIS_ENTITY_OWN, ANALYSIS_FILTER_ALL, dateRangeDays, formatDateRangeLabel } from "@/lib/analysis";
import { regionDisplay, regionFromMonitoringScope, SETUP_REGIONS } from "@/lib/setup";
import type { AnalysisFilters } from "@/types";
import { cn } from "@/lib/utils";

export type FilterSelectProps = {
  icon: LucideIcon;
  value: string;
  displayValue?: string;
  placeholder: string;
  disabled?: boolean;
  title?: string;
  onValueChange?: (value: string) => void;
  children?: ReactNode;
  className?: string;
};

export function FilterSelect({
  icon: Icon,
  value,
  displayValue,
  placeholder,
  disabled,
  title,
  onValueChange,
  children,
  className,
}: FilterSelectProps) {
  return (
    <Select value={value} onValueChange={onValueChange} disabled={disabled}>
      <SelectTrigger
        title={title}
        className={cn(
          "border-border h-9 w-auto gap-2 rounded-lg bg-white px-3 text-xs font-normal shadow-none",
          "hover:border-border hover:shadow-none",
          "focus:border-border focus:shadow-none focus:ring-0",
          "focus-visible:border-border focus-visible:shadow-none focus-visible:ring-0",
          "data-[state=open]:border-border data-[state=open]:shadow-none data-[state=open]:ring-0",
          disabled && "opacity-60",
          className,
        )}
      >
        <Icon className="text-muted-foreground size-3.5 shrink-0" aria-hidden />
        <span className="truncate text-foreground">
          {displayValue ?? placeholder}
        </span>
      </SelectTrigger>
      {children ? <SelectContent>{children}</SelectContent> : null}
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
  /** 平台页矩阵需展示全部平台，隐藏平台筛选 */
  hidePlatformFilter?: boolean;
};

/** 分析页筛选条：分析对象、时间、地区、主题、平台。 */
export function AnalysisFilterBar({
  value,
  onChange,
  afterFilters,
  trailing,
  hideEntityFilter = false,
  hidePlatformFilter = false,
}: AnalysisFilterBarProps) {
  const { subject } = useDashboardContext();
  const { entities, topics, platforms } = useAnalysisFilter();

  const setupRegionId = useMemo(
    () => regionFromMonitoringScope(subject.monitoring_scope),
    [subject.monitoring_scope],
  );
  const regionOption = useMemo(
    () => SETUP_REGIONS.find((r) => r.value === setupRegionId) ?? SETUP_REGIONS[0],
    [setupRegionId],
  );

  const { days, entityId, platformId, topicId, regionId } = value;
  const { from, to } = useMemo(() => dateRangeDays(Number(days)), [days]);
  const selectedEntity = entities.find((entity) => entity.id === entityId);
  const selectedTopic = topics.find((t) => t.id === topicId);
  const selectedPlatform = platforms.find((p) => p.platform === platformId);
  const topicDisplay =
    topicId === ANALYSIS_FILTER_ALL ? "所有主题" : (selectedTopic?.name ?? "所有主题");
  const platformDisplay =
    platformId === ANALYSIS_FILTER_ALL ? "所有平台" : (selectedPlatform?.label ?? "所有平台");
  const regionDisplayLabel =
    regionId === ANALYSIS_FILTER_ALL
      ? "所有地区"
      : (SETUP_REGIONS.find((r) => r.value === regionId)?.label ?? regionDisplay(setupRegionId));

  return (
    <div className="flex w-full max-w-full min-w-0 flex-wrap items-center gap-2 border-b px-4 py-3">
      {!hideEntityFilter ? (
        <FilterSelect
          icon={Tag}
          value={entityId || ANALYSIS_ENTITY_OWN}
          displayValue={selectedEntity?.display_name ?? "本品牌"}
          placeholder="分析对象"
          onValueChange={(id) => onChange((prev) => ({ ...prev, entityId: id }))}
          disabled={entities.length === 0}
        >
          {entities.map((entity) => (
            <SelectItem key={entity.id} value={entity.id}>
              {entity.display_name}
            </SelectItem>
          ))}
        </FilterSelect>
      ) : null}

      <FilterSelect
        icon={Calendar}
        value={days}
        displayValue={formatDateRangeLabel(from, to)}
        placeholder="选择时间范围"
        onValueChange={(id) => onChange((prev) => ({ ...prev, days: id }))}
      >
        {ANALYSIS_DATE_OPTIONS.map((opt) => (
          <SelectItem key={opt.value} value={opt.value}>
            {opt.label}
          </SelectItem>
        ))}
      </FilterSelect>

      <FilterSelect
        icon={MapPin}
        value={regionId}
        displayValue={regionDisplayLabel}
        placeholder="所有地区"
        onValueChange={(id) => onChange((prev) => ({ ...prev, regionId: id }))}
      >
        <SelectItem value={ANALYSIS_FILTER_ALL}>所有地区</SelectItem>
        <SelectItem value={regionOption.value}>
          {regionOption.flag ? `${regionOption.flag} ` : ""}
          {regionOption.label}
        </SelectItem>
      </FilterSelect>

      <FilterSelect
        icon={Hash}
        value={topicId}
        displayValue={topicDisplay}
        placeholder="所有主题"
        onValueChange={(id) => onChange((prev) => ({ ...prev, topicId: id }))}
      >
        <SelectItem value={ANALYSIS_FILTER_ALL}>所有主题</SelectItem>
        {topics.map((topic) => (
          <SelectItem key={topic.id} value={topic.id}>
            {topic.name}
          </SelectItem>
        ))}
      </FilterSelect>

      {!hidePlatformFilter ? (
        <FilterSelect
          icon={Bot}
          value={platformId}
          displayValue={platformDisplay}
          placeholder="所有平台"
          onValueChange={(id) => onChange((prev) => ({ ...prev, platformId: id }))}
          disabled={platforms.length === 0}
        >
          <SelectItem value={ANALYSIS_FILTER_ALL}>所有平台</SelectItem>
          {platforms.map((platform) => (
            <SelectItem key={platform.platform} value={platform.platform}>
              {platform.label}
            </SelectItem>
          ))}
        </FilterSelect>
      ) : null}

      {afterFilters}

      {trailing ? (
        <div className="ml-auto flex min-w-0 shrink-0 flex-wrap items-center gap-2">{trailing}</div>
      ) : null}
    </div>
  );
}
