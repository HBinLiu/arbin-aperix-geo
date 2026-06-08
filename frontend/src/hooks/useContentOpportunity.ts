import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchContentOpportunities } from "@/api/analysis";
import { dateRangeDays, toAnalysisQueryFilters } from "@/lib/analysis";
import {
  buildContentOpportunityRows,
  filterContentOpportunityRows,
} from "@/lib/opportunity/content";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters } from "@/types";

export function useContentOpportunity(
  subjectId: string,
  filters: AnalysisFilters,
  search: string,
  enabled = true,
) {
  const queryFilters = toAnalysisQueryFilters(filters);
  const { from, to } = useMemo(() => dateRangeDays(Number(filters.days)), [filters.days]);
  const { topicId, platformId } = queryFilters;

  const query = useQuery({
    queryKey: queryKeys.contentOpportunities(subjectId, from, to, topicId, platformId),
    queryFn: () => fetchContentOpportunities(subjectId, from, to, queryFilters),
    enabled,
  });

  const rows = useMemo(() => {
    const built = buildContentOpportunityRows(query.data?.items ?? []);
    return filterContentOpportunityRows(built, search);
  }, [query.data?.items, search]);

  return {
    isLoading: query.isLoading,
    rows,
  };
}
