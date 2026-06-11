import type { AnalysisFilters, AnalysisQueryFilters } from "@/types";

export const ANALYSIS_FILTER_ALL = "all" as const;
export const ANALYSIS_ENTITY_OWN = "own" as const;

export const ANALYSIS_DATE_OPTIONS = [
  { value: "7", label: "最近 7 天" },
  { value: "30", label: "最近 30 天" },
] as const;

export const DEFAULT_ANALYSIS_FILTERS: AnalysisFilters = {
  days: "30",
  entityId: ANALYSIS_ENTITY_OWN,
  platformId: ANALYSIS_FILTER_ALL,
  topicId: ANALYSIS_FILTER_ALL,
  regionId: ANALYSIS_FILTER_ALL,
};

export function toAnalysisQueryFilters(filters: AnalysisFilters): AnalysisQueryFilters {
  const { entityId, platformId, topicId, regionId } = filters;
  return { entityId, platformId, topicId, regionId };
}

export function analysisFilterKey(filters: AnalysisQueryFilters): [string, string, string, string] {
  return [filters.entityId, filters.platformId, filters.topicId, filters.regionId];
}

export function buildAnalysisParams(
  from: string,
  to: string,
  filters?: AnalysisQueryFilters,
  promptId?: string | null,
  host?: string | null,
): Record<string, string | string[]> {
  const params: Record<string, string | string[]> = {};
  if (filters?.entityId && filters.entityId !== ANALYSIS_ENTITY_OWN) {
    params.entity_id = filters.entityId;
  }
  if (filters?.platformId && filters.platformId !== ANALYSIS_FILTER_ALL) {
    params.platform = filters.platformId;
  }
  if (filters?.topicId && filters.topicId !== ANALYSIS_FILTER_ALL) {
    params.topic_id = filters.topicId;
  }
  if (promptId) {
    params.prompt_id = promptId;
  }
  if (host) {
    params.host = host;
  }
  params.from = from;
  params.to = to;
  return params;
}

/** FastAPI 列表 query 需重复 key，而非 platform[]。 */
export const ANALYSIS_PARAMS_SERIALIZER = { indexes: null } as const;
