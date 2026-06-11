import { useQuery } from "@tanstack/react-query";

import { fetchVisibilityAnalysis } from "@/api/analysis";
import { dateRangeDays, toAnalysisQueryFilters } from "@/lib/analysis";
import {
  buildVisibilityMetricBundles,
  type VisibilityMetricBundle,
  type VisibilityMetricId,
} from "@/lib/analysis/visibility";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters } from "@/types";

export type { VisibilityMetricBundle, VisibilityMetricId };

/** 可见度页指标数据（可见度 + AI 提及，一次请求含当前 + 上一周期） */
export function useVisibilityAnalysis(subjectId: string, filters: AnalysisFilters) {
  const queryFilters = toAnalysisQueryFilters(filters);
  const { from, to } = dateRangeDays(Number(filters.days));
  const { entityId, platformId, topicId } = queryFilters;

  const query = useQuery({
    queryKey: queryKeys.visibilityAnalysis(subjectId, entityId, platformId, topicId, from, to),
    queryFn: () => fetchVisibilityAnalysis(subjectId, queryFilters, from, to),
  });

  const data = query.data;
  const ownLabel = data?.own_label ?? "";
  const topicVisibilityRanks =
    data?.topic_visibility_ranks.map((row) => ({
      topicId: row.topic_id,
      topicName: row.topic_name,
      ranks: row.ranks,
    })) ?? [];

  return {
    isLoading: query.isLoading,
    ownLabel,
    topLabels: data?.labels ?? [],
    topicVisibilityRanks,
    metrics: buildVisibilityMetricBundles(data, ownLabel),
  };
}
