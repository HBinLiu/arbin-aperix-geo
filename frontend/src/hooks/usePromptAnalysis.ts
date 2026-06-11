import { useMemo } from "react";

import { fetchPromptsPerformance, fetchTopicsPerformance } from "@/api/analysis";
import { dateRangeDays, previousDateRange, toAnalysisQueryFilters } from "@/lib/analysis";
import {
  buildPromptPerformanceRows,
  buildTopicPerformanceRows,
} from "@/lib/analysis/prompt";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters } from "@/types";
import { useQueries } from "@tanstack/react-query";

export function usePromptAnalysis(subjectId: string, filters: AnalysisFilters) {
  const queryFilters = toAnalysisQueryFilters(filters);
  const { from, to } = useMemo(() => dateRangeDays(Number(filters.days)), [filters.days]);
  const prevRange = useMemo(() => previousDateRange(from, to), [from, to]);
  const { entityId, platformId, topicId } = queryFilters;

  const [topicsCurrent, topicsPrevious, promptsCurrent, promptsPrevious] = useQueries({
    queries: [
      {
        queryKey: queryKeys.analysisTopics(subjectId, entityId, platformId, topicId, from, to),
        queryFn: () => fetchTopicsPerformance(subjectId, queryFilters, from, to),
      },
      {
        queryKey: queryKeys.analysisTopics(
          subjectId,
          entityId,
          platformId,
          topicId,
          prevRange.from,
          prevRange.to,
        ),
        queryFn: () =>
          fetchTopicsPerformance(subjectId, queryFilters, prevRange.from, prevRange.to),
      },
      {
        queryKey: queryKeys.analysisPrompts(subjectId, entityId, platformId, topicId, from, to),
        queryFn: () => fetchPromptsPerformance(subjectId, queryFilters, from, to),
      },
      {
        queryKey: queryKeys.analysisPrompts(
          subjectId,
          entityId,
          platformId,
          topicId,
          prevRange.from,
          prevRange.to,
        ),
        queryFn: () =>
          fetchPromptsPerformance(subjectId, queryFilters, prevRange.from, prevRange.to),
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
    () => buildPromptPerformanceRows(promptsCurrent.data ?? [], promptsPrevious.data ?? []),
    [promptsCurrent.data, promptsPrevious.data],
  );

  return { isLoading, topicRows, promptRows };
}

export function filterPromptRowsBySearch<T extends { promptText: string; topicName: string }>(
  rows: T[],
  search: string,
): T[] {
  const query = search.trim().toLowerCase();
  if (!query) return rows;
  return rows.filter(
    (row) =>
      row.promptText.toLowerCase().includes(query) ||
      row.topicName.toLowerCase().includes(query),
  );
}

export function filterPromptRowsByTopic<T extends { topicId: string | null }>(
  rows: T[],
  topicId: string | null | undefined,
): T[] {
  if (!topicId) return rows;
  return rows.filter((row) => row.topicId === topicId);
}
