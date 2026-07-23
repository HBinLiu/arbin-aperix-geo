import { useMemo } from "react";

import { fetchPromptFanoutOpportunities } from "@/api/analysis";
import { platformFilterKey, topicFilterKey, toAnalysisQueryFilters } from "@/lib/analysis";
import { paginatedListResult, usePaginatedQuery } from "@/hooks/usePaginatedQuery";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters } from "@/types";

export type PromptFanoutListRequest = {
  page: number;
  pageSize: number;
  search: string;
};

export function usePromptFanoutOpportunities(
  subjectId: string,
  filters: AnalysisFilters,
  listRequest: PromptFanoutListRequest,
  enabled = true,
) {
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to, platformIds, topicIds } = queryFilters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);
  const { page, pageSize, search } = listRequest;
  const searchKey = search.trim();

  const query = usePaginatedQuery({
    queryKey: queryKeys.promptFanoutOpportunities(
      subjectId,
      platformKey,
      topicKey,
      from,
      to,
      searchKey,
      page,
      pageSize,
    ),
    queryFn: () =>
      fetchPromptFanoutOpportunities(subjectId, queryFilters, {
        page,
        pageSize,
        search: searchKey || undefined,
        status: "pending",
      }),
    enabled,
  });

  const list = paginatedListResult(query, { page, pageSize });
  return { ...list, rows: query.data?.items ?? [], refetch: query.refetch };
}
