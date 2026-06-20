import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchCitationAnalysis } from "@/api/analysis";
import { platformFilterKey, topicFilterKey, toAnalysisQueryFilters } from "@/lib/analysis";

import { buildCitationOverview } from "@/lib/analysis/citation";
import { queryKeys } from "@/lib/queries";
import type { AnalysisEntityRef, AnalysisFilters } from "@/types";

export function useCitationAnalysis(
  subjectId: string,
  filters: AnalysisFilters,
  entities: AnalysisEntityRef[],
) {
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to, entityId, platformIds, topicIds } = queryFilters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);

  const query = useQuery({
    queryKey: queryKeys.citationAnalysis(subjectId, entityId, platformKey, topicKey, from, to),
    queryFn: () => fetchCitationAnalysis(subjectId, queryFilters),
  });

  const data = query.data;

  return {
    isLoading: query.isLoading,
    data,
    ownLabel: data?.focus_label ?? data?.own_label ?? "",
    overview: buildCitationOverview(data, entities, entityId),
  };
}
