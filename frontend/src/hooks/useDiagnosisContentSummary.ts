import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchDiagnosisContentSummary } from "@/api/analysis";
import { platformFilterKey, topicFilterKey, toAnalysisQueryFilters } from "@/lib/analysis";
import { diagnosisContentOverview } from "@/lib/diagnosis/content";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters } from "@/types";

export function useDiagnosisContentSummary(
  subjectId: string,
  filters: AnalysisFilters,
  enabled = true,
) {
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to, entityId, platformIds, topicIds } = queryFilters;
  const platformKey = platformFilterKey(platformIds);
  const topicKey = topicFilterKey(topicIds);

  const query = useQuery({
    queryKey: queryKeys.diagnosisContentSummary(
      subjectId,
      entityId,
      platformKey,
      topicKey,
      from,
      to,
    ),
    queryFn: () => fetchDiagnosisContentSummary(subjectId, queryFilters),
    enabled,
  });

  const overview = useMemo(
    () => diagnosisContentOverview(query.data?.summary),
    [query.data?.summary],
  );

  return {
    isLoading: query.isLoading,
    overview,
  };
}
