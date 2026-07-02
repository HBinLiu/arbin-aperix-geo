import { useMemo } from "react";

import { fetchDiagnosisContent } from "@/api/analysis";
import { useAnalysisFilter } from "@/hooks/useAnalysisFilter";
import { platformFilterKey, topicFilterKey, toAnalysisQueryFilters } from "@/lib/analysis";
import { buildDiagnosisContentRows } from "@/lib/diagnosis/content";
import { paginatedListResult, usePaginatedQuery } from "@/hooks/usePaginatedQuery";
import { queryKeys } from "@/lib/queries";
import type { AnalysisFilters, ContentOpportunitySortField } from "@/types";

export type DiagnosisContentListRequest = {
  page: number;
  pageSize: number;
  sortBy?: ContentOpportunitySortField | null;
  order?: "asc" | "desc";
};

export function useDiagnosisContent(
  subjectId: string,
  filters: AnalysisFilters,
  listRequest: DiagnosisContentListRequest,
  enabled = true,
) {
  const { entities } = useAnalysisFilter();
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to, entityId, platformIds, topicIds } = queryFilters;
  const platformKey = platformFilterKey(platformIds);
  const topicKey = topicFilterKey(topicIds);
  const { page, pageSize, sortBy, order } = listRequest;
  const sortKey = sortBy ?? "";

  const query = usePaginatedQuery({
    queryKey: queryKeys.diagnosisContent(
      subjectId,
      entityId,
      platformKey,
      topicKey,
      from,
      to,
      page,
      pageSize,
      sortKey,
      order ?? "",
    ),
    queryFn: () =>
      fetchDiagnosisContent(subjectId, queryFilters, {
        page,
        pageSize,
        sortBy,
        order,
      }),
    enabled,
  });

  const list = paginatedListResult(query, { page, pageSize });
  const rows = useMemo(
    () => buildDiagnosisContentRows(query.data?.items ?? [], entities),
    [entities, query.data?.items],
  );

  return { ...list, rows };
}
