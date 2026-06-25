import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchPlatformAnalysis } from "@/api/analysis";
import { useAnalysisFilter } from "@/hooks/useAnalysisFilter";
import { platformFilterKey, topicFilterKey, toAnalysisQueryFilters } from "@/lib/analysis";

import {
  buildPlatformMatrixRows,
  buildPlatformMetricBundles,
  platformMatrixMetric,
} from "@/lib/analysis/platform";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters, PlatformMatrixMetricId, PlatformMatrixRowDimension } from "@/types";

export function usePlatformAnalysis(
  subjectId: string,
  filters: AnalysisFilters,
  rowDimension: PlatformMatrixRowDimension,
  metricId: PlatformMatrixMetricId,
  chartPlatformIds: string[],
) {
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to, entityId, platformIds, topicIds } = queryFilters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);
  const metric = platformMatrixMetric(metricId);
  const { entities, topics, platformCatalog, isLoading: catalogLoading } = useAnalysisFilter();

  const analysisQuery = useQuery({
    queryKey: queryKeys.platformAnalysis(
      subjectId,
      entityId,
      platformKey,
      topicKey,
      from,
      to,
      rowDimension,
    ),
    queryFn: () => fetchPlatformAnalysis(subjectId, queryFilters, rowDimension),
  });

  const data = analysisQuery.data;

  return {
    isLoading: analysisQuery.isLoading || catalogLoading,
    data,
    metric,
    matrixRows: data ? buildPlatformMatrixRows(data, rowDimension, metricId, entities, topics) : [],
    platformMetrics: buildPlatformMetricBundles(data, chartPlatformIds, platformCatalog),
  };
}
