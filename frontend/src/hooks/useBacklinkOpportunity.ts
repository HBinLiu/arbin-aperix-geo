import { useMemo } from "react";

import { fetchBacklinkOpportunities } from "@/api/analysis";
import { platformFilterKey, topicFilterKey, toAnalysisQueryFilters } from "@/lib/analysis";
import { buildBacklinkOpportunityRows } from "@/lib/opportunity/backlink";
import { paginatedListResult, usePaginatedQuery } from "@/hooks/usePaginatedQuery";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters, BacklinkOpportunitySortField } from "@/types";

export type BacklinkOpportunityListRequest = {
  page: number;
  pageSize: number;
  search: string;
  sortBy?: BacklinkOpportunitySortField | null;
  order?: "asc" | "desc";
};

export function useBacklinkOpportunity(
  subjectId: string,
  filters: AnalysisFilters,
  listRequest: BacklinkOpportunityListRequest,
  enabled = true,
) {
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to, entityId, platformIds, topicIds } = queryFilters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);
  const { page, pageSize, search, sortBy, order } = listRequest;
  const searchKey = search.trim();
  const sortKey = sortBy ?? "";

  const query = usePaginatedQuery({
    queryKey: queryKeys.backlinkOpportunities(
      subjectId,
      entityId,
      platformKey,
      topicKey,
      from,
      to,
      searchKey,
      page,
      pageSize,
      sortKey,
      order ?? "",
    ),
    queryFn: () =>
      fetchBacklinkOpportunities(subjectId, queryFilters, {
        page,
        pageSize,
        search: searchKey || undefined,
        sortBy,
        order,
      }),
    enabled,
  });

  const list = paginatedListResult(query, { page, pageSize });
  const rows = useMemo(
    () => buildBacklinkOpportunityRows(query.data?.items ?? []),
    [query.data?.items],
  );

  return { ...list, rows };
}
