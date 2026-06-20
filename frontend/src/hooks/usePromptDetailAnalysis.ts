import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchPromptDetail } from "@/api/analysis";
import { fetchSubjectPrompts, fetchSubjectTopics } from "@/api/brand";
import { platformFilterKey, topicFilterKey, toAnalysisQueryFilters } from "@/lib/analysis";
import {
  promptDetailMetric,
  type PromptDetailMetricId,
} from "@/lib/analysis/promptDetail";
import { queryKeys, sessionCatalogQueryOptions } from "@/lib/queries";
import type { AnalysisFilters, PlatformPerformance, PromptDetailData } from "@/types";

export function usePromptDetailMeta(subjectId: string, promptId: string) {
  const promptsQuery = useQuery({
    queryKey: queryKeys.subjectPrompts(subjectId),
    queryFn: () => fetchSubjectPrompts(subjectId),
  });
  const topicsQuery = useQuery({
    queryKey: queryKeys.subjectTopics(subjectId),
    queryFn: () => fetchSubjectTopics(subjectId),
    ...sessionCatalogQueryOptions,
  });

  const prompt = promptsQuery.data?.find((item) => item.id === promptId);
  const topic = topicsQuery.data?.find((item) => item.id === prompt?.topic_id);

  return {
    isLoading: promptsQuery.isLoading || topicsQuery.isLoading,
    promptText: prompt?.text ?? "",
    topicName: topic?.name ?? "",
    intent: prompt?.search_intent ?? null,
  };
}

function toPlatformPerformance(rows: PromptDetailData["platforms"]): PlatformPerformance[] {
  return rows.map((row) => ({
    platform: row.platform,
    visibility_rate: row.visibility_rate,
    mention_rate: null,
    share_voice: null,
    average_rank: row.average_rank,
    citation_rate: row.citation_rate,
    sentiment_score: null,
    sentiment_label: null,
  }));
}

export function usePromptDetailAnalysis(
  subjectId: string,
  promptId: string,
  filters: AnalysisFilters,
) {
  const queryFilters = useMemo(
    () => ({ ...toAnalysisQueryFilters(filters), topicIds: [] as string[] }),
    [filters],
  );
  const { from, to, entityId, platformIds, topicIds } = queryFilters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);

  const detailQuery = useQuery({
    queryKey: queryKeys.promptDetail(
      subjectId,
      entityId,
      platformKey,
      topicKey,
      promptId,
      from,
      to,
    ),
    queryFn: () => fetchPromptDetail(subjectId, queryFilters, promptId),
    enabled: Boolean(promptId),
  });

  const data = detailQuery.data;

  const cardValues = useMemo(() => {
    if (!data) return {};
    return {
      visibility: promptDetailMetric("visibility").formatValue(data.visibility_rate),
      averageRank: promptDetailMetric("averageRank").formatValue(data.average_rank),
      citation: promptDetailMetric("citation").formatValue(data.citation_rate),
    };
  }, [data]);

  const lineSeriesByMetric = useMemo(
    (): Record<PromptDetailMetricId, { date: string; value: number | null }[]> => ({
      visibility: data?.visibility_series ?? [],
      averageRank: data?.average_rank_series ?? [],
      citation: data?.citation_series ?? [],
    }),
    [data],
  );

  return {
    isLoading: detailQuery.isLoading,
    cardValues,
    platforms: toPlatformPerformance(data?.platforms ?? []),
    lineSeriesByMetric,
    opportunity: data?.opportunity ?? null,
    responses: data ?? null,
    promptText: data?.prompt_text ?? "",
  };
}
