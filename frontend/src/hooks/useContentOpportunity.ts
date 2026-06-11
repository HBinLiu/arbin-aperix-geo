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
  const { entityId, platformId, topicId } = queryFilters;

  const query = useQuery({
    queryKey: queryKeys.contentOpportunities(subjectId, entityId, platformId, topicId, from, to),
    queryFn: () => fetchContentOpportunities(subjectId, queryFilters, from, to),
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
