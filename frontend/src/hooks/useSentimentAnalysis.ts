import { useQuery } from "@tanstack/react-query";

import { fetchSentimentAnalysis } from "@/api/analysis";
import { fetchSamplingPlatforms } from "@/api/brand";
import { dateRangeDays, toAnalysisQueryFilters } from "@/lib/analysis";
import { buildSentimentOverview } from "@/lib/analysis/sentiment";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters } from "@/types";

export function useSentimentAnalysis(subjectId: string, filters: AnalysisFilters) {
  const queryFilters = toAnalysisQueryFilters(filters);
  const { from, to } = dateRangeDays(Number(filters.days));
  const { entityId, platformId, topicId } = queryFilters;

  const analysisQuery = useQuery({
    queryKey: queryKeys.sentimentAnalysis(subjectId, entityId, platformId, topicId, from, to),
    queryFn: () => fetchSentimentAnalysis(subjectId, queryFilters, from, to),
  });

  const platformsMetaQuery = useQuery({
    queryKey: queryKeys.samplingPlatforms,
    queryFn: fetchSamplingPlatforms,
  });

  const data = analysisQuery.data;
  const platformsMeta = platformsMetaQuery.data ?? [];

  return {
    isLoading: analysisQuery.isLoading || platformsMetaQuery.isLoading,
    data,
    overview: buildSentimentOverview(data, platformsMeta),
  };
}
