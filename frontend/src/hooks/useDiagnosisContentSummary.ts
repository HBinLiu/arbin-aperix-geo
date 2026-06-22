import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchDiagnosisContentSummary } from "@/api/analysis";
import { diagnosisContentOverview } from "@/lib/diagnosis/content";
import { queryKeys } from "@/lib/queries";

export function useDiagnosisContentSummary(subjectId: string, enabled = true) {
  const query = useQuery({
    queryKey: queryKeys.diagnosisContentSummary(subjectId),
    queryFn: () => fetchDiagnosisContentSummary(subjectId),
    enabled,
  });

  const overview = useMemo(
    () => diagnosisContentOverview(query.data?.summary),
    [query.data?.summary],
  );

  return {
    isLoading: query.isLoading,
    overview,
  };
}
