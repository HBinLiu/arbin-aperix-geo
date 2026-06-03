import type { AnalysisFilters, AnalysisQueryFilters } from "@/types";

export const ANALYSIS_FILTER_ALL = "all" as const;

export const ANALYSIS_DATE_OPTIONS = [
  { value: "7", label: "最近 7 天" },
  { value: "30", label: "最近 30 天" },
] as const;

export const DEFAULT_ANALYSIS_FILTERS: AnalysisFilters = {
  days: "30",
  regionId: ANALYSIS_FILTER_ALL,
  topicId: ANALYSIS_FILTER_ALL,
  platformId: ANALYSIS_FILTER_ALL,
};

export function toAnalysisQueryFilters(filters: AnalysisFilters): AnalysisQueryFilters {
  const { regionId, topicId, platformId } = filters;
  return { regionId, topicId, platformId };
}

export function analysisFilterKey(filters: AnalysisQueryFilters): [string, string, string] {
  return [filters.regionId, filters.topicId, filters.platformId];
}

export function buildAnalysisParams(
  from: string,
  to: string,
  filters?: AnalysisQueryFilters,
): Record<string, string | string[]> {
  const params: Record<string, string | string[]> = { from, to };
  if (filters?.topicId && filters.topicId !== ANALYSIS_FILTER_ALL) {
    params.topic_id = filters.topicId;
  }
  if (filters?.platformId && filters.platformId !== ANALYSIS_FILTER_ALL) {
    params.platform = filters.platformId;
  }
  return params;
}

/** FastAPI 列表 query 需重复 key，而非 platform[]。 */
export const ANALYSIS_PARAMS_SERIALIZER = { indexes: null } as const;
