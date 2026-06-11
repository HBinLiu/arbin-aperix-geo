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
  const { entityId, platformId, topicId } = queryFilters;

  const query = useQuery({
    queryKey: queryKeys.backlinkOpportunities(subjectId, entityId, platformId, topicId, from, to),
    queryFn: () => fetchBacklinkOpportunities(subjectId, queryFilters, from, to),
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
