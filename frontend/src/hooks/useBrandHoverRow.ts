import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchSubjectCompetitors } from "@/api/brand";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { resolveBrandHoverRow } from "@/lib/brand/hoverRow";
import { queryKeys, sessionCatalogQueryOptions } from "@/lib/queries";
import type { CompetitorItem } from "@/types";

export function useBrandHoverRow(label: string, override?: CompetitorItem): CompetitorItem {
  const { subject } = useDashboardContext();
  const { data } = useQuery({
    queryKey: queryKeys.subjectCompetitors(subject.id),
    queryFn: () => fetchSubjectCompetitors(subject.id),
    ...sessionCatalogQueryOptions,
  });

  return useMemo(
    () => override ?? resolveBrandHoverRow(label, subject, data?.competitors ?? []),
    [override, label, subject, data?.competitors],
  );
}
