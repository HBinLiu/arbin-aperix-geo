import { useQuery } from "@tanstack/react-query";

import { fetchPlatformMatrix } from "@/api/analysis";
import { fetchSamplingPlatforms } from "@/api/brand";
import { dateRangeDays, toAnalysisQueryFilters } from "@/lib/analysis";
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
  selectedPlatformId: string | null,
) {
  const queryFilters = toAnalysisQueryFilters(filters);
  const { from, to } = dateRangeDays(Number(filters.days));
  const { entityId, platformId, topicId } = queryFilters;
  const metric = platformMatrixMetric(metricId);

  const matrixQuery = useQuery({
    queryKey: queryKeys.platformMatrix(subjectId, entityId, platformId, topicId, from, to),
    queryFn: () => fetchPlatformMatrix(subjectId, queryFilters, from, to),
  });

  const platformsMetaQuery = useQuery({
    queryKey: queryKeys.samplingPlatforms,
    queryFn: fetchSamplingPlatforms,
  });

  const data = matrixQuery.data;
  const platformsMeta = platformsMetaQuery.data ?? [];

  return {
    isLoading: matrixQuery.isLoading || platformsMetaQuery.isLoading,
    data,
    platformsMeta,
    metric,
    matrixRows: data ? buildPlatformMatrixRows(data, rowDimension, metricId) : [],
    platformMetrics: buildPlatformMetricBundles(data, selectedPlatformId, platformsMeta),
  };
}
