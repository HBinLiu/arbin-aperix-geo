import { useMemo } from "react";

import {
  fetchPromptsPerformance,
  type FetchPromptsPerformanceOptions,
} from "@/api/analysis";
import { fetchTopicsPerformance } from "@/api/analysis";
import { previousDateRange, platformFilterKey, topicFilterKey, toAnalysisQueryFilters, withAnalysisDateRange } from "@/lib/analysis";

import {
  buildPromptPerformanceRows,
  buildTopicPerformanceRows,
} from "@/lib/analysis/prompt";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters } from "@/types";
import { useQueries } from "@tanstack/react-query";

export type PromptListRequest = {
  page: number;
  pageSize: number;
  search: string;
  topicId: string | null;
  sortBy: FetchPromptsPerformanceOptions["sortBy"];
  order: "asc" | "desc";
};

export function usePromptAnalysis(
  subjectId: string,
  filters: AnalysisFilters,
  listRequest: PromptListRequest,
) {
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const prevQueryFilters = useMemo(() => {
    const prev = previousDateRange(queryFilters.from, queryFilters.to);
    return withAnalysisDateRange(queryFilters, prev.from, prev.to);
  }, [queryFilters]);
  const { from, to, entityId, platformIds, topicIds } = queryFilters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);
  const {
    page,
    pageSize,
    search,
    topicId: listTopicId,
    sortBy,
    order,
  } = listRequest;
  const searchKey = search.trim();
  const listTopicKey = listTopicId ?? "";
  const sortKey = sortBy ?? "";
  const promptFetchOptions = useMemo(
    (): FetchPromptsPerformanceOptions => ({
      page,
      pageSize,
      search: searchKey || undefined,
      topicId: listTopicId,
      sortBy,
      order,
    }),
    [page, pageSize, searchKey, listTopicId, sortBy, order],
  );

  const [topicsCurrent, topicsPrevious, promptsCurrent, promptsPrevious] = useQueries({
    queries: [
      {
        queryKey: queryKeys.analysisTopics(subjectId, entityId, platformKey, topicKey, from, to),
        queryFn: () => fetchTopicsPerformance(subjectId, queryFilters),
      },
      {
        queryKey: queryKeys.analysisTopics(
          subjectId,
          entityId,
          platformKey, topicKey, prevQueryFilters.from,
          prevQueryFilters.to,
        ),
        queryFn: () => fetchTopicsPerformance(subjectId, prevQueryFilters),
      },
      {
        queryKey: queryKeys.analysisPrompts(
          subjectId,
          entityId,
          platformKey,
          topicKey,
          from,
          to,
          page,
          pageSize,
          searchKey,
          listTopicKey,
          sortKey,
          order,
        ),
        queryFn: () => fetchPromptsPerformance(subjectId, queryFilters, promptFetchOptions),
      },
      {
        queryKey: queryKeys.analysisPrompts(
          subjectId,
          entityId,
          platformKey,
          topicKey,
          prevQueryFilters.from,
          prevQueryFilters.to,
          page,
          pageSize,
          searchKey,
          listTopicKey,
          sortKey,
          order,
        ),
        queryFn: () => fetchPromptsPerformance(subjectId, prevQueryFilters, promptFetchOptions),
      },
    ],
  });

  const isLoading =
    topicsCurrent.isLoading ||
    topicsPrevious.isLoading ||
    promptsCurrent.isLoading ||
    promptsPrevious.isLoading;

  const topicRows = useMemo(
    () => buildTopicPerformanceRows(topicsCurrent.data ?? [], topicsPrevious.data ?? []),
    [topicsCurrent.data, topicsPrevious.data],
  );

  const promptRows = useMemo(
    () =>
      buildPromptPerformanceRows(
        promptsCurrent.data?.items ?? [],
        promptsPrevious.data?.items ?? [],
      ),
    [promptsCurrent.data?.items, promptsPrevious.data?.items],
  );

  return {
    isLoading,
    topicRows,
    promptRows,
    promptTotal: promptsCurrent.data?.total ?? 0,
    promptPage: promptsCurrent.data?.page ?? page,
    promptPageSize: promptsCurrent.data?.page_size ?? pageSize,
  };
}
