import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchAnalysisResponses } from "@/api/analysis";
import type { FetchAnalysisResponsesOptions } from "@/api/analysis";
import { platformFilterKey, topicFilterKey, toAnalysisQueryFilters } from "@/lib/analysis";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters, AnalysisResponseSortField, SentimentTab } from "@/types";

export function useAnalysisResponses(
  subjectId: string,
  filters: AnalysisFilters,
  options: FetchAnalysisResponsesOptions & { enabled?: boolean },
) {
  const { enabled = true, ...requestOptions } = options;
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to, entityId, platformIds, topicIds } = queryFilters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);
  const sentimentLabel = requestOptions.sentimentLabel ?? null;
  const page = requestOptions.page ?? 1;
  const pageSize = requestOptions.pageSize ?? 10;
  const sortBy = requestOptions.sortBy ?? null;
  const order = requestOptions.order ?? "desc";

  const responsesQuery = useQuery({
    queryKey: queryKeys.analysisResponses(
      subjectId,
      entityId,
      platformKey,
      topicKey,
      from,
      to,
      sentimentLabel,
      requestOptions.promptId,
      page,
      pageSize,
      sortBy,
      order,
    ),
    queryFn: () =>
      fetchAnalysisResponses(subjectId, queryFilters, {
        ...requestOptions,
        page,
        pageSize,
        sortBy,
        order,
      }),
    enabled,
  });

  return {
    isLoading: responsesQuery.isLoading,
    responses: responsesQuery.data?.items ?? [],
    total: responsesQuery.data?.total ?? 0,
    page: responsesQuery.data?.page ?? page,
    pageSize: responsesQuery.data?.page_size ?? pageSize,
  };
}

export function useSentimentTabResponses(
  subjectId: string,
  filters: AnalysisFilters,
  sentimentLabel: SentimentTab,
  pagination: {
    page: number;
    pageSize: number;
    sortBy: "created_at" | "sentiment_score" | null;
    order: "asc" | "desc";
  },
) {
  return useAnalysisResponses(subjectId, filters, {
    sentimentLabel,
    page: pagination.page,
    pageSize: pagination.pageSize,
    sortBy: pagination.sortBy,
    order: pagination.order,
  });
}

export function usePromptDetailChatResponses(
  subjectId: string,
  promptId: string,
  filters: AnalysisFilters,
  pagination: {
    page: number;
    pageSize: number;
    sortBy?: AnalysisResponseSortField | null;
    order?: "asc" | "desc";
  },
  enabled = true,
) {
  return useAnalysisResponses(subjectId, filters, {
    promptId,
    page: pagination.page,
    pageSize: pagination.pageSize,
    sortBy: pagination.sortBy ?? null,
    order: pagination.order ?? "desc",
    enabled: enabled && Boolean(promptId),
  });
}
