import { dateRangeDays } from "@/lib/analysis/date";
import type { AnalysisFilters, AnalysisQueryFilters } from "@/types";

export const ANALYSIS_FILTER_ALL = "all" as const;
export const ANALYSIS_ENTITY_OWN = "own" as const;

export const ANALYSIS_DATE_PRESETS = [
  { days: 7, label: "最近 7 天" },
  { days: 14, label: "最近 14 天" },
  { days: 30, label: "最近 30 天" },
] as const;

/** @deprecated 使用 ANALYSIS_DATE_PRESETS */
export const ANALYSIS_DATE_OPTIONS = ANALYSIS_DATE_PRESETS.map((preset) => ({
  value: String(preset.days),
  label: preset.label,
}));

export const DEFAULT_ANALYSIS_FILTERS: AnalysisFilters = {
  ...dateRangeDays(7),
  entityId: ANALYSIS_ENTITY_OWN,
  platformIds: [],
  topicIds: [],
};

/** 空数组表示全部平台；排序仅用于 query key，不影响展示顺序。 */
export function platformFilterKey(platformIds: string[] | undefined): string {
  const ids = platformIds ?? [];
  if (ids.length === 0) return ANALYSIS_FILTER_ALL;
  return [...ids].sort().join(",");
}

/** 矩阵列顺序：有筛选时按用户选择顺序；否则用主体已配置平台顺序。 */
export function matrixPlatformIds(
  platformIds: string[],
  configuredPlatformIds: string[],
): string[] {
  if (platformIds.length > 0) return platformIds;
  return configuredPlatformIds;
}

/** 空数组表示全部主题；否则为排序后的 id 列表拼接（用于 query key） */
export function topicFilterKey(topicIds: string[] | undefined): string {
  const ids = topicIds ?? [];
  if (ids.length === 0) return ANALYSIS_FILTER_ALL;
  return [...ids].sort().join(",");
}

export function toAnalysisQueryFilters(filters: AnalysisFilters): AnalysisQueryFilters {
  const { entityId, platformIds, topicIds, from, to } = filters;
  return {
    entityId,
    platformIds: platformIds ?? [],
    topicIds: topicIds ?? [],
    from,
    to,
  };
}

export function withAnalysisDateRange(
  filters: AnalysisQueryFilters,
  from: string,
  to: string,
): AnalysisQueryFilters {
  return { ...filters, from, to };
}

export function analysisFilterKey(filters: AnalysisQueryFilters): [string, string, string] {
  return [
    filters.entityId,
    platformFilterKey(filters.platformIds),
    topicFilterKey(filters.topicIds),
  ];
}

export function buildAnalysisParams(
  filters: AnalysisQueryFilters,
  promptId?: string | null,
  host?: string | null,
): Record<string, string | string[]> {
  const params: Record<string, string | string[]> = {};
  if (filters.entityId !== ANALYSIS_ENTITY_OWN) {
    params.entity_id = filters.entityId;
  }
  if ((filters.platformIds ?? []).length > 0) {
    params.platform = filters.platformIds;
  }
  if ((filters.topicIds ?? []).length > 0) {
    params.topic_id = filters.topicIds;
  }
  if (promptId) {
    params.prompt_id = promptId;
  }
  if (host) {
    params.host = host;
  }
  params.start_date = filters.from;
  params.end_date = filters.to;
  return params;
}

/** FastAPI 列表 query 需重复 key，而非 platform[]。 */
export const ANALYSIS_PARAMS_SERIALIZER = { indexes: null } as const;
