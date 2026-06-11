import { useMemo } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";

import {
  fetchCitationAnalysis,
  fetchContentOpportunities,
  fetchPlatformPerformance,
  fetchPromptDetail,
  fetchPromptsPerformance,
  fetchVisibilityAnalysis,
} from "@/api/analysis";
import { fetchSubjectPrompts, fetchSubjectTopics } from "@/api/brand";
import { dateRangeDays, previousDateRange, toAnalysisQueryFilters } from "@/lib/analysis";
import {
  aggregatePromptOpportunity,
  extractOwnShareSeries,
  promptPerformanceSummary,
  type PromptDetailMetricId,
} from "@/lib/analysis/promptDetail";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters } from "@/types";

export function usePromptDetailMeta(subjectId: string, promptId: string) {
  const promptsQuery = useQuery({
    queryKey: queryKeys.brandPrompts(subjectId),
    queryFn: () => fetchSubjectPrompts(subjectId),
  });
  const topicsQuery = useQuery({
    queryKey: queryKeys.subjectTopics(subjectId),
    queryFn: () => fetchSubjectTopics(subjectId),
  });

  const prompt = promptsQuery.data?.find((item) => item.id === promptId);
  const topic = topicsQuery.data?.find((item) => item.id === prompt?.topic_id);

  return {
    isLoading: promptsQuery.isLoading || topicsQuery.isLoading,
    promptText: prompt?.text ?? "",
    topicName: topic?.name ?? "",
    intent: null as string | null,
  };
}

export function usePromptDetailAnalysis(
  subjectId: string,
  promptId: string,
  filters: AnalysisFilters,
) {
  const queryFilters = toAnalysisQueryFilters(filters);
  const { from, to } = useMemo(() => dateRangeDays(Number(filters.days)), [filters.days]);
  const prevRange = useMemo(() => previousDateRange(from, to), [from, to]);
  const { entityId, platformId, topicId } = queryFilters;

  const [visibilityCurrent, citationCurrent, platformsCurrent, promptsCurrent, promptsPrevious, opportunities, responses] =
    useQueries({
    queries: [
      {
        queryKey: queryKeys.promptDetailVisibility(
          subjectId,
          entityId,
          platformId,
          topicId,
          promptId,
          from,
          to,
        ),
        queryFn: () =>
          fetchVisibilityAnalysis(subjectId, queryFilters, from, to, promptId),
      },
      {
        queryKey: queryKeys.promptDetailCitation(
          subjectId,
          entityId,
          platformId,
          topicId,
          promptId,
          from,
          to,
        ),
        queryFn: () =>
          fetchCitationAnalysis(subjectId, queryFilters, from, to, promptId),
      },
      {
        queryKey: queryKeys.promptDetailPlatforms(
          subjectId,
          entityId,
          platformId,
          topicId,
          promptId,
          from,
          to,
        ),
        queryFn: () =>
          fetchPlatformPerformance(subjectId, queryFilters, from, to, promptId),
      },
      {
        queryKey: queryKeys.promptDetailPrompts(
          subjectId,
          entityId,
          platformId,
          topicId,
          promptId,
          from,
          to,
        ),
        queryFn: () => fetchPromptsPerformance(subjectId, queryFilters, from, to),
      },
      {
        queryKey: queryKeys.promptDetailPrompts(
          subjectId,
          entityId,
          platformId,
          topicId,
          promptId,
          prevRange.from,
          prevRange.to,
        ),
        queryFn: () =>
          fetchPromptsPerformance(subjectId, queryFilters, prevRange.from, prevRange.to),
      },
      {
        queryKey: queryKeys.promptDetailOpportunities(
          subjectId,
          entityId,
          platformId,
          topicId,
          promptId,
          from,
          to,
        ),
        queryFn: () =>
          fetchContentOpportunities(subjectId, queryFilters, from, to, promptId),
      },
      {
        queryKey: queryKeys.promptDetailResponses(
          subjectId,
          entityId,
          platformId,
          topicId,
          promptId,
          from,
          to,
        ),
        queryFn: () => fetchPromptDetail(subjectId, queryFilters, from, to, promptId),
      },
    ],
  });

  const isLoading =
    visibilityCurrent.isLoading ||
    citationCurrent.isLoading ||
    platformsCurrent.isLoading ||
    promptsCurrent.isLoading ||
    promptsPrevious.isLoading ||
    opportunities.isLoading ||
    responses.isLoading;

  const visibilityData = visibilityCurrent.data;
  const citationData = citationCurrent.data;
  const ownLabel =
    visibilityData?.focus_label ??
    visibilityData?.own_label ??
    citationData?.focus_label ??
    citationData?.own_label ??
    "";

  const summary = useMemo(() => {
    const current = promptPerformanceSummary(promptsCurrent.data ?? [], promptId);
    const previous = promptPerformanceSummary(promptsPrevious.data ?? [], promptId);
    return { current, previous };
  }, [promptId, promptsCurrent.data, promptsPrevious.data]);

  const opportunity = useMemo(
    () => aggregatePromptOpportunity(opportunities.data?.items ?? []),
    [opportunities.data?.items],
  );

  const lineSeriesByMetric = useMemo(
    (): Record<PromptDetailMetricId, ReturnType<typeof extractOwnShareSeries>> => ({
      visibility: extractOwnShareSeries(visibilityData?.series ?? [], ownLabel),
      averageRank: (visibilityData?.average_rank_series ?? []).map((point) => ({
        date: point.date,
        value: point.value,
      })),
      citation: extractOwnShareSeries(citationData?.series ?? [], ownLabel),
    }),
    [visibilityData, citationData, ownLabel],
  );

  return {
    isLoading,
    ownLabel,
    summary,
    platforms: platformsCurrent.data ?? [],
    lineSeriesByMetric,
    opportunity,
    responses: responses.data ?? null,
    responsesLoading: responses.isLoading,
  };
}
