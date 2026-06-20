import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchContentOpportunityDetail } from "@/api/analysis";
import { ANALYSIS_ENTITY_OWN, platformFilterKey, topicFilterKey, toAnalysisQueryFilters } from "@/lib/analysis";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters } from "@/types";

export function useContentOpportunityDetail(
  subjectId: string,
  filters: AnalysisFilters,
  options: {
    promptId: string;
    enabled?: boolean;
  },
) {
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to, platformIds, topicIds } = queryFilters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);

  return useQuery({
    queryKey: queryKeys.contentOpportunityDetail(
      subjectId,
      ANALYSIS_ENTITY_OWN,
      platformKey,
      topicKey,
      from,
      to,
      options.promptId,
    ),
    queryFn: () =>
      fetchContentOpportunityDetail(subjectId, queryFilters, {
        promptId: options.promptId,
      }),
    enabled: (options.enabled ?? true) && !!options.promptId,
  });
}
