import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchRank } from "@/api/analysis";
import { dateRangeDays, toAnalysisQueryFilters } from "@/lib/analysis";
import { buildRankBoardRows } from "@/lib/dashboard/rank";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters } from "@/types";

/** 排行榜页：品牌竞品全指标排名 */
export function useRankBoardData(subjectId: string, filters: AnalysisFilters) {
  const queryFilters = toAnalysisQueryFilters(filters);
  const { from, to } = useMemo(() => dateRangeDays(Number(filters.days)), [filters.days]);
  const { entityId, platformId, topicId } = queryFilters;

  const query = useQuery({
    queryKey: queryKeys.analysisRank(subjectId, entityId, platformId, topicId, from, to),
    queryFn: () => fetchRank(subjectId, queryFilters, from, to),
  });

  const rows = useMemo(
    () => (query.data ? buildRankBoardRows(query.data) : []),
    [query.data],
  );

  return {
    isLoading: query.isLoading,
    data: query.data,
    rows,
  };
}
