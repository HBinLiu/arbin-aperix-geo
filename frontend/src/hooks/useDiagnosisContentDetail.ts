import { useQuery } from "@tanstack/react-query";

import { fetchDiagnosisContentDetail } from "@/api/analysis";
import { queryKeys } from "@/lib/queries";

export function useDiagnosisContentDetail(
  subjectId: string,
  options: {
    promptId: string;
    enabled?: boolean;
  },
) {
  return useQuery({
    queryKey: queryKeys.diagnosisContentDetail(subjectId, options.promptId),
    queryFn: () =>
      fetchDiagnosisContentDetail(subjectId, {
        promptId: options.promptId,
      }),
    enabled: (options.enabled ?? true) && !!options.promptId,
  });
}
