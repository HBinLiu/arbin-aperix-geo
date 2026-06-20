import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchCitationDomainAnalysis } from "@/api/analysis";
import { platformFilterKey, topicFilterKey, toAnalysisQueryFilters } from "@/lib/analysis";

import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters } from "@/types";

export function useCitationDomainAnalysis(
  subjectId: string,
  host: string,
  filters: AnalysisFilters,
) {
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to, entityId, platformIds, topicIds } = queryFilters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);

  const query = useQuery({
    queryKey: queryKeys.citationDomainAnalysis(
      subjectId,
      entityId,
      platformKey, topicKey, host,
      from,
      to,
    ),
    queryFn: () => fetchCitationDomainAnalysis(subjectId, queryFilters, host),
    enabled: Boolean(host),
  });

  return {
    isLoading: query.isLoading,
    data: query.data,
  };
}
