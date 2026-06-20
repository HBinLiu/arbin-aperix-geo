import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchContentOpportunities } from "@/api/analysis";
import { ANALYSIS_ENTITY_OWN, platformFilterKey, topicFilterKey, toAnalysisQueryFilters } from "@/lib/analysis";

import { buildContentOpportunityRows } from "@/lib/opportunity/content";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters, ContentOpportunitySortField } from "@/types";

export type ContentOpportunityListRequest = {
  page: number;
  pageSize: number;
  search: string;
  sortBy?: ContentOpportunitySortField | null;
  order?: "asc" | "desc";
};

export function useContentOpportunity(
  subjectId: string,
  filters: AnalysisFilters,
  listRequest: ContentOpportunityListRequest,
  enabled = true,
) {
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to, platformIds, topicIds } = queryFilters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);
  const { page, pageSize, search, sortBy, order } = listRequest;
  const searchKey = search.trim();
  const sortKey = sortBy ?? "";

  const query = useQuery({
    queryKey: queryKeys.contentOpportunities(
      subjectId,
      ANALYSIS_ENTITY_OWN,
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
      fetchContentOpportunities(subjectId, queryFilters, {
        page,
        pageSize,
        search: searchKey || undefined,
        sortBy,
        order,
      }),
    enabled,
  });

  const rows = useMemo(
    () => buildContentOpportunityRows(query.data?.items ?? []),
    [query.data?.items],
  );

  return {
    isLoading: query.isLoading,
    rows,
    total: query.data?.total ?? 0,
    page: query.data?.page ?? page,
    pageSize: query.data?.page_size ?? pageSize,
  };
}
