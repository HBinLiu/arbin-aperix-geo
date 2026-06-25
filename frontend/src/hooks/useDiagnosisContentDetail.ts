import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchDiagnosisContentDetail } from "@/api/analysis";
import { platformFilterKey, topicFilterKey, toAnalysisQueryFilters } from "@/lib/analysis";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters } from "@/types";

export function useDiagnosisContentDetail(
  subjectId: string,
  filters: AnalysisFilters,
  options: {
    promptId: string;
    enabled?: boolean;
  },
) {
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to, entityId, platformIds, topicIds } = queryFilters;
  const platformKey = platformFilterKey(platformIds);
  const topicKey = topicFilterKey(topicIds);

  return useQuery({
    queryKey: queryKeys.diagnosisContentDetail(
      subjectId,
      options.promptId,
      entityId,
      platformKey,
      topicKey,
      from,
      to,
    ),
    queryFn: () =>
      fetchDiagnosisContentDetail(subjectId, queryFilters, {
        promptId: options.promptId,
      }),
    enabled: (options.enabled ?? true) && !!options.promptId,
  });
}
