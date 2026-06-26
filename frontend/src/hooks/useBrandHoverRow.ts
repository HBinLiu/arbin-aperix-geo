import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchSubjectCompetitors } from "@/api/brand";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { resolveBrandHoverRow, type BrandHoverHints } from "@/lib/brand/hoverRow";
import { queryKeys, sessionCatalogQueryOptions } from "@/lib/queries";
import type { CompetitorItem } from "@/types";

export function useBrandHoverRow(
  label: string,
  override?: CompetitorItem,
  domainHint?: string | null,
): CompetitorItem {
  const { subject } = useDashboardContext();
  const { data } = useQuery({
    queryKey: queryKeys.subjectCompetitors(subject.id),
    queryFn: () => fetchSubjectCompetitors(subject.id),
    ...sessionCatalogQueryOptions,
  });

  return useMemo(() => {
    const hints = domainHint?.trim() ? { domain: domainHint.trim() } : undefined;
    return override ?? resolveBrandHoverRow(label, subject, data?.competitors ?? [], hints);
  }, [override, domainHint, label, subject, data?.competitors]);
}
