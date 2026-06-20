import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchSentimentAnalysis } from "@/api/analysis";
import { platformFilterKey, topicFilterKey, toAnalysisQueryFilters } from "@/lib/analysis";
import { buildSentimentOverview } from "@/lib/analysis/sentiment";
import { queryKeys } from "@/lib/queries";
import type { AnalysisEntityRef, AnalysisFilters } from "@/types";

export function useSentimentAnalysis(
  subjectId: string,
  filters: AnalysisFilters,
  entities: AnalysisEntityRef[],
) {
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to, entityId, platformIds, topicIds } = queryFilters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);

  const analysisQuery = useQuery({
    queryKey: queryKeys.sentimentAnalysis(subjectId, entityId, platformKey, topicKey, from, to),
    queryFn: () => fetchSentimentAnalysis(subjectId, queryFilters),
  });

  return {
    isLoading: analysisQuery.isLoading,
    data: analysisQuery.data,
    overview: buildSentimentOverview(analysisQuery.data, entities, entityId),
  };
}
