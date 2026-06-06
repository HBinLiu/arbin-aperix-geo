import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchRank } from "@/api/analysis";
import { buildBrandLeaderboardRows } from "@/lib/dashboard/rank";
import { dateRangeDays, toAnalysisQueryFilters } from "@/lib/analysis";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters } from "@/types";

/** 排行榜页：品牌竞品全指标排名 */
export function useBrandRank(subjectId: string, filters: AnalysisFilters) {
  const queryFilters = toAnalysisQueryFilters(filters);
  const { from, to } = useMemo(() => dateRangeDays(Number(filters.days)), [filters.days]);
  const { topicId, platformId } = queryFilters;

  const query = useQuery({
    queryKey: queryKeys.analysisRank(subjectId, from, to, topicId, platformId),
    queryFn: () => fetchRank(subjectId, from, to, queryFilters),
  });

  const rows = useMemo(
    () => (query.data ? buildBrandLeaderboardRows(query.data) : []),
    [query.data],
  );

  return {
    isLoading: query.isLoading,
    data: query.data,
    rows,
  };
}
