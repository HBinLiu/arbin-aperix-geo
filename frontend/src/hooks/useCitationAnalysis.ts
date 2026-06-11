import { useQuery } from "@tanstack/react-query";

import { fetchCitationAnalysis } from "@/api/analysis";
import { dateRangeDays, toAnalysisQueryFilters } from "@/lib/analysis";
import { buildCitationOverview } from "@/lib/analysis/citation";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters } from "@/types";

export function useCitationAnalysis(subjectId: string, filters: AnalysisFilters) {
  const queryFilters = toAnalysisQueryFilters(filters);
  const { from, to } = dateRangeDays(Number(filters.days));
  const { entityId, platformId, topicId } = queryFilters;

  const query = useQuery({
    queryKey: queryKeys.citationAnalysis(subjectId, entityId, platformId, topicId, from, to),
    queryFn: () => fetchCitationAnalysis(subjectId, queryFilters, from, to),
  });

  const data = query.data;

  return {
    isLoading: query.isLoading,
    data,
    ownLabel: data?.focus_label ?? data?.own_label ?? "",
    topLabels: data?.labels ?? [],
    overview: buildCitationOverview(data),
  };
}
