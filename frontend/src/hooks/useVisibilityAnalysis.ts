import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchVisibilityAnalysis } from "@/api/analysis";
import {
  entityChartLabels,
  focusEntityLabel,
  ownEntityLabel,
  platformFilterKey,
  topicFilterKey,
  toAnalysisQueryFilters,
} from "@/lib/analysis";

import {
  buildVisibilityMetricBundles,
  type VisibilityMetricBundle,
  type VisibilityMetricId,
} from "@/lib/analysis/visibility";
import { queryKeys } from "@/lib/queries";
import type { AnalysisEntityRef, AnalysisFilters } from "@/types";

export type { VisibilityMetricBundle, VisibilityMetricId };

/** 可见度页指标数据（可见度 + AI 提及，一次请求含当前 + 上一周期） */
export function useVisibilityAnalysis(
  subjectId: string,
  filters: AnalysisFilters,
  entities: AnalysisEntityRef[],
) {
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to, entityId, platformIds, topicIds } = queryFilters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);
  const entityLabels = useMemo(() => entityChartLabels(entities), [entities]);
  const ownLabel = useMemo(() => ownEntityLabel(entities), [entities]);

  const query = useQuery({
    queryKey: queryKeys.visibilityAnalysis(subjectId, entityId, platformKey, topicKey, from, to),
    queryFn: () => fetchVisibilityAnalysis(subjectId, queryFilters),
  });

  const data = query.data;
  const focusLabel = useMemo(
    () => focusEntityLabel(entities, data?.entity_id ?? entityId),
    [data?.entity_id, entityId, entities],
  );
  const focusEntityId = data?.entity_id ?? entityId;
  const topicVisibilityRanks =
    data?.topic_visibility_ranks.map((row) => ({
      topicId: row.topic_id,
      topicName: row.topic_name,
      ranks: row.ranks,
    })) ?? [];

  return {
    isLoading: query.isLoading,
    ownLabel,
    focusLabel,
    topicVisibilityRanks,
    metrics: buildVisibilityMetricBundles(data, entityLabels, entities, focusEntityId),
  };
}
