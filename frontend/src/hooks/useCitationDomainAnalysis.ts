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
  const { entityId, platformId, topicId } = queryFilters;

  const query = useQuery({
    queryKey: queryKeys.citationDomainAnalysis(
      subjectId,
      entityId,
      platformId,
      topicId,
      host,
      from,
      to,
    ),
    queryFn: () => fetchCitationDomainAnalysis(subjectId, queryFilters, host, from, to),
    enabled: Boolean(host),
  });

  return {
    isLoading: query.isLoading,
    data: query.data,
  };
}
