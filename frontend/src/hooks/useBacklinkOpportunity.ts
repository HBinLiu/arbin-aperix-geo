import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchBacklinkOpportunities } from "@/api/analysis";
import { dateRangeDays, toAnalysisQueryFilters } from "@/lib/analysis";
import {
  buildBacklinkOpportunityRows,
  filterBacklinkOpportunityRows,
} from "@/lib/opportunity/backlink";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters } from "@/types";

export function useBacklinkOpportunity(
  subjectId: string,
  filters: AnalysisFilters,
  search: string,
  enabled = true,
) {
  const queryFilters = toAnalysisQueryFilters(filters);
  const { from, to } = useMemo(() => dateRangeDays(Number(filters.days)), [filters.days]);
  const { topicId, platformId } = queryFilters;

  const query = useQuery({
    queryKey: queryKeys.backlinkOpportunities(subjectId, from, to, topicId, platformId),
    queryFn: () => fetchBacklinkOpportunities(subjectId, from, to, queryFilters),
    enabled,
  });

  const rows = useMemo(() => {
    const built = buildBacklinkOpportunityRows(query.data?.items ?? []);
    return filterBacklinkOpportunityRows(built, search);
  }, [query.data?.items, search]);

  return {
    isLoading: query.isLoading,
    rows,
  };
}
