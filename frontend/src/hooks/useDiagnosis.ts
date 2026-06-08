import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchDiagnosis } from "@/api/analysis";
import { dateRangeDays, toAnalysisQueryFilters } from "@/lib/analysis";
import {
  buildDiagnosisMentionRows,
  buildDiagnosisPromptRows,
  diagnosisOverview,
} from "@/lib/diagnosis";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters } from "@/types";

export function useDiagnosis(subjectId: string, filters: AnalysisFilters) {
  const queryFilters = toAnalysisQueryFilters(filters);
  const { from, to } = useMemo(() => dateRangeDays(Number(filters.days)), [filters.days]);
  const { topicId, platformId } = queryFilters;

  const query = useQuery({
    queryKey: queryKeys.diagnosis(subjectId, from, to, topicId, platformId),
    queryFn: () => fetchDiagnosis(subjectId, from, to, queryFilters),
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
