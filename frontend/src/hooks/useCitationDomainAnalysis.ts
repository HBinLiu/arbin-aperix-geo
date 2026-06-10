import { useQuery } from "@tanstack/react-query";

import { fetchCitationDomainAnalysis } from "@/api/analysis";
import { dateRangeDays, toAnalysisQueryFilters } from "@/lib/analysis";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters } from "@/types";

export function useCitationDomainAnalysis(
  subjectId: string,
  host: string,
  filters: AnalysisFilters,
) {
  const queryFilters = toAnalysisQueryFilters(filters);
  const { from, to } = dateRangeDays(Number(filters.days));
  const { topicId, platformId } = queryFilters;

  const query = useQuery({
    queryKey: queryKeys.citationDomainAnalysis(subjectId, host, from, to, topicId, platformId),
    queryFn: () => fetchCitationDomainAnalysis(subjectId, host, from, to, queryFilters),
    enabled: Boolean(host),
  });

  return {
    isLoading: query.isLoading,
    data: query.data,
  };
}
