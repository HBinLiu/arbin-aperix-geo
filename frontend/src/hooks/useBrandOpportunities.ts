import { useMemo } from "react";

import { fetchBrands } from "@/api/analysis";
import { platformFilterKey, topicFilterKey, toAnalysisQueryFilters } from "@/lib/analysis";
import { buildBrandRows } from "@/lib/opportunity/brand";
import { paginatedListResult, usePaginatedQuery } from "@/hooks/usePaginatedQuery";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters, BrandSortField } from "@/types";

export type BrandListRequest = {
  page: number;
  pageSize: number;
  search: string;
  sortBy?: BrandSortField | null;
  order?: "asc" | "desc";
};

export function useBrandOpportunities(
  subjectId: string,
  filters: AnalysisFilters,
  listRequest: BrandListRequest,
  enabled = true,
) {
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to, platformIds, topicIds } = queryFilters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);
  const { page, pageSize, search, sortBy, order } = listRequest;
  const searchKey = search.trim();
  const sortKey = sortBy ?? "";

  const query = usePaginatedQuery({
    queryKey: queryKeys.brandOpportunities(
      subjectId,
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
      fetchBrands(subjectId, queryFilters, {
        page,
        pageSize,
        search: searchKey || undefined,
        sortBy,
        order,
      }),
    enabled,
  });

  const list = paginatedListResult(query, { page, pageSize });
  const rows = useMemo(() => buildBrandRows(query.data?.items ?? []), [query.data?.items]);

  return { ...list, rows, refetch: query.refetch };
}
