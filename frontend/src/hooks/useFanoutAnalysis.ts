import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchFanoutAnalysis, fetchFanoutPrompts, fetchFanoutQueries } from "@/api/analysis";
import { platformFilterKey, topicFilterKey, toAnalysisQueryFilters } from "@/lib/analysis";
import { buildFanoutOverview } from "@/lib/analysis/fanout";
import { queryKeys } from "@/lib/queries";
import { usePlatformCatalog } from "@/hooks/usePlatformCatalog";
import type { AnalysisFilters, FanoutPromptSortField } from "@/types";

export function useFanoutAnalysis(subjectId: string, filters: AnalysisFilters) {
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to, platformIds, topicIds } = queryFilters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);
  const platformCatalog = usePlatformCatalog();

  const query = useQuery({
    queryKey: queryKeys.fanoutAnalysis(subjectId, platformKey, topicKey, from, to),
    queryFn: () => fetchFanoutAnalysis(subjectId, queryFilters),
  });

  return {
    isLoading: query.isLoading,
    data: query.data,
    overview: buildFanoutOverview(query.data, platformCatalog),
  };
}

export function useFanoutPrompts(
  subjectId: string,
  filters: AnalysisFilters,
  options: {
    page: number;
    pageSize: number;
    sortBy?: FanoutPromptSortField;
    order?: "asc" | "desc";
    search?: string;
  },
) {
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to, platformIds, topicIds } = queryFilters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);
  const search = options.search?.trim() ?? "";

  const query = useQuery({
    queryKey: queryKeys.fanoutPrompts(
      subjectId,
      platformKey,
      topicKey,
      from,
      to,
      options.page,
      options.pageSize,
      options.sortBy ?? "quantity",
      options.order ?? "desc",
      search,
    ),
    queryFn: () =>
      fetchFanoutPrompts(subjectId, queryFilters, {
        page: options.page,
        pageSize: options.pageSize,
        sortBy: options.sortBy,
        order: options.order,
        search,
      }),
  });

  return {
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    rows: query.data?.items ?? [],
    total: query.data?.total ?? 0,
  };
}

export function useFanoutQueries(
  subjectId: string,
  promptId: string,
  filters: AnalysisFilters,
  options: {
    page: number;
    pageSize: number;
    enabled?: boolean;
  },
) {
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to, platformIds, topicIds } = queryFilters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);
  const enabled = Boolean(promptId) && (options.enabled ?? true);

  const query = useQuery({
    queryKey: queryKeys.fanoutQueries(
      subjectId,
      promptId,
      platformKey,
      topicKey,
      from,
      to,
      options.page,
      options.pageSize,
    ),
    queryFn: () =>
      fetchFanoutQueries(subjectId, queryFilters, {
        promptId,
        page: options.page,
        pageSize: options.pageSize,
      }),
    enabled,
  });

  return {
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    rows: query.data?.items ?? [],
    total: query.data?.total ?? 0,
  };
}
