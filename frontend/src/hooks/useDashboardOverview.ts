import { useMemo } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";

import { fetchOverview, fetchTopicsPerformance } from "@/api/analysis";
import { useCitationAnalysis } from "@/hooks/useCitationAnalysis";
import { useVisibilityAnalysis } from "@/hooks/useVisibilityAnalysis";
import { dateRangeDays, previousDateRange, toAnalysisQueryFilters } from "@/lib/analysis";
import { buildTopicPerformanceRows } from "@/lib/analysis/prompt";
import { ownBrandRank } from "@/lib/dashboard/overview";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters } from "@/types";

/** 概述页：核心指标 + 可见度趋势/排名 + 主题表现 */
export function useDashboardOverview(subjectId: string, filters: AnalysisFilters) {
  const queryFilters = toAnalysisQueryFilters(filters);
  const { from, to } = useMemo(() => dateRangeDays(Number(filters.days)), [filters.days]);
  const prevRange = useMemo(() => previousDateRange(from, to), [from, to]);
  const { entityId, platformId, topicId } = queryFilters;

  const overviewQuery = useQuery({
    queryKey: queryKeys.analysisOverview(subjectId, entityId, platformId, topicId, from, to),
    queryFn: () => fetchOverview(subjectId, queryFilters, from, to),
  });

  const [topicsCurrent, topicsPrevious] = useQueries({
    queries: [
      {
        queryKey: queryKeys.analysisTopics(subjectId, entityId, platformId, topicId, from, to),
        queryFn: () => fetchTopicsPerformance(subjectId, queryFilters, from, to),
      },
      {
        queryKey: queryKeys.analysisTopics(
          subjectId,
          entityId,
          platformId,
          topicId,
          prevRange.from,
          prevRange.to,
        ),
        queryFn: () =>
          fetchTopicsPerformance(subjectId, queryFilters, prevRange.from, prevRange.to),
      },
    ],
  });

  const visibility = useVisibilityAnalysis(subjectId, filters);
  const citation = useCitationAnalysis(subjectId, filters);

  const visibilityMetrics = visibility.metrics;
  const citationOverview = citation.overview;

  const topicRows = useMemo(
    () => buildTopicPerformanceRows(topicsCurrent.data ?? [], topicsPrevious.data ?? []),
    [topicsCurrent.data, topicsPrevious.data],
  );

  const topicLoading = topicsCurrent.isLoading || topicsPrevious.isLoading;

  return {
    isLoading:
      overviewQuery.isLoading ||
      visibility.isLoading ||
      citation.isLoading ||
      topicLoading,
    overview: overviewQuery.data,
    ownLabel: visibility.ownLabel,
    topLabels: visibility.topLabels,
    visibilityMetric: visibilityMetrics.visibility,
    citationOverview,
    topicRows,
    ranks: {
      visibility: ownBrandRank(visibilityMetrics.visibility.rankRows),
      citation: ownBrandRank(citationOverview.rankRows),
      shareVoice: ownBrandRank(visibilityMetrics.shareVoice.rankRows),
    },
  };
}
