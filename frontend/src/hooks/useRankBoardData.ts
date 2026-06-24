import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchRank } from "@/api/analysis";
import { platformFilterKey, topicFilterKey, toAnalysisQueryFilters } from "@/lib/analysis";

import { buildRankBoardRows } from "@/lib/dashboard/rank";
import { queryKeys } from "@/lib/queries";
import { useAnalysisCatalogEnabled } from "@/hooks/useAnalysisCatalogEnabled";
import type { AnalysisFilters } from "@/types";

/** 排行榜页：品牌竞品全指标排名 */
export function useRankBoardData(subjectId: string, filters: AnalysisFilters) {
  const catalogEnabled = useAnalysisCatalogEnabled();
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to, entityId, platformIds, topicIds } = queryFilters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);

  const query = useQuery({
    queryKey: queryKeys.analysisRank(subjectId, entityId, platformKey, topicKey, from, to),
    queryFn: () => fetchRank(subjectId, queryFilters),
    enabled: catalogEnabled,
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
