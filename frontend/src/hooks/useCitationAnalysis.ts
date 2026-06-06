import { useQuery } from "@tanstack/react-query";

import { fetchCitationAnalysis } from "@/api/analysis";
import { dateRangeDays, toAnalysisQueryFilters } from "@/lib/analysis";
import { buildCitationOverview } from "@/lib/analysis/citation";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters } from "@/types";

export function useCitationAnalysis(subjectId: string, filters: AnalysisFilters) {
  const queryFilters = toAnalysisQueryFilters(filters);
  const { from, to } = dateRangeDays(Number(filters.days));
  const { topicId, platformId } = queryFilters;

  const query = useQuery({
    queryKey: queryKeys.citationAnalysis(subjectId, from, to, topicId, platformId),
    queryFn: () => fetchCitationAnalysis(subjectId, from, to, queryFilters),
  });

  const data = query.data;

  return {
    isLoading: query.isLoading,
    data,
    ownLabel: data?.own_label ?? "",
    topLabels: data?.labels ?? [],
    overview: buildCitationOverview(data),
  };
}
