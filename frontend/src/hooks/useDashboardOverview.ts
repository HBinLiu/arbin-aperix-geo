import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchOverview } from "@/api/analysis";
import {
  focusEntityLabel,
  platformFilterKey,
  topicFilterKey,
  toAnalysisQueryFilters,
} from "@/lib/analysis";

import {
  buildDashboardTopicRows,
  buildDashboardVisibilityMetric,
  dashboardOverviewView,
} from "@/lib/dashboard/overview";
import { queryKeys } from "@/lib/queries";
import type { AnalysisEntityRef, AnalysisFilters } from "@/types";

/** 概述页：单次请求加载 KPI、可见度趋势、主题表现与排名 */
export function useDashboardOverview(
  subjectId: string,
  filters: AnalysisFilters,
  entities: AnalysisEntityRef[],
  options?: { enabled?: boolean },
) {
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to, entityId, platformIds, topicIds } = queryFilters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);

  const query = useQuery({
    queryKey: queryKeys.dashboardOverview(subjectId, entityId, platformKey, topicKey, from, to),
    queryFn: () => fetchOverview(subjectId, queryFilters),
    enabled: options?.enabled ?? true,
  });

  const data = query.data;
  const focusLabel = useMemo(
    () => focusEntityLabel(entities, data?.entity_id ?? entityId),
    [data?.entity_id, entityId, entities],
  );
  const focusEntityId = data?.entity_id ?? entityId;
  const metrics = useMemo(() => dashboardOverviewView(data), [data]);
  const visibilityMetric = useMemo(
    () => buildDashboardVisibilityMetric(data, entities, focusEntityId),
    [data, entities, focusEntityId],
  );
  const topicRows = useMemo(() => buildDashboardTopicRows(data?.topic_table), [data?.topic_table]);

  return {
    isLoading: query.isLoading,
    metrics,
    focusLabel,
    visibilityMetric,
    topicRows,
  };
}
