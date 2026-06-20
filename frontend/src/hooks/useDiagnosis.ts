import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchDiagnosis } from "@/api/analysis";
import { platformFilterKey, topicFilterKey, toAnalysisQueryFilters } from "@/lib/analysis";

import {
  buildDiagnosisMentionRows,
  buildDiagnosisPromptRows,
  diagnosisOverview,
} from "@/lib/diagnosis";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters } from "@/types";

export function useDiagnosis(subjectId: string, filters: AnalysisFilters) {
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to, entityId, platformIds, topicIds } = queryFilters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);

  const query = useQuery({
    queryKey: queryKeys.diagnosis(subjectId, entityId, platformKey, topicKey, from, to),
    queryFn: () => fetchDiagnosis(subjectId, queryFilters),
  });

  const overview = useMemo(() => diagnosisOverview(query.data), [query.data]);

  const mentionRows = useMemo(
    () => buildDiagnosisMentionRows(query.data?.mention_items ?? []),
    [query.data?.mention_items],
  );

  const promptRows = useMemo(
    () => buildDiagnosisPromptRows(query.data?.prompt_items ?? []),
    [query.data?.prompt_items],
  );

  return {
    isLoading: query.isLoading,
    overview,
    mentionRows,
    promptRows,
  };
}
