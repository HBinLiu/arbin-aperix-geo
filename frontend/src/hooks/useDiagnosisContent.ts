import { useMemo } from "react";

import { fetchDiagnosisContent } from "@/api/analysis";
import { buildDiagnosisContentRows } from "@/lib/diagnosis/content";
import { paginatedListResult, usePaginatedQuery } from "@/hooks/usePaginatedQuery";
import { queryKeys } from "@/lib/queries";
import type { ContentOpportunitySortField } from "@/types";

export type DiagnosisContentListRequest = {
  page: number;
  pageSize: number;
  sortBy?: ContentOpportunitySortField | null;
  order?: "asc" | "desc";
};

export function useDiagnosisContent(
  subjectId: string,
  listRequest: DiagnosisContentListRequest,
  enabled = true,
) {
  const { page, pageSize, sortBy, order } = listRequest;
  const sortKey = sortBy ?? "";

  const query = usePaginatedQuery({
    queryKey: queryKeys.diagnosisContent(subjectId, page, pageSize, sortKey, order ?? ""),
    queryFn: () =>
      fetchDiagnosisContent(subjectId, {
        page,
        pageSize,
        sortBy,
        order,
      }),
    enabled,
  });

  const list = paginatedListResult(query, { page, pageSize });
  const rows = useMemo(
    () => buildDiagnosisContentRows(query.data?.items ?? []),
    [query.data?.items],
  );

  return { ...list, rows };
}
