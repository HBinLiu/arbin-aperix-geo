import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchAnalysisEntities } from "@/api/analysis";
import { fetchSamplingPlatforms, fetchSubjectTopics } from "@/api/brand";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { useAnalysisCatalogEnabled } from "@/hooks/useAnalysisCatalogEnabled";
import {
  effectiveSamplingPlatforms,
} from "@/lib/brand";
import { queryKeys, sessionCatalogQueryOptions } from "@/lib/queries";

/** 分析页筛选项：实体目录、主题列表、主体已选平台。 */
export function useAnalysisFilter(options?: { enabled?: boolean }) {
  const { subject } = useDashboardContext();
  const catalogEnabled = useAnalysisCatalogEnabled(options?.enabled);

  const entitiesQuery = useQuery({
    queryKey: queryKeys.analysisEntities(subject.id),
    queryFn: () => fetchAnalysisEntities(subject.id),
    ...sessionCatalogQueryOptions,
    enabled: catalogEnabled,
  });

  const topicsQuery = useQuery({
    queryKey: queryKeys.subjectTopics(subject.id),
    queryFn: () => fetchSubjectTopics(subject.id),
    ...sessionCatalogQueryOptions,
    enabled: catalogEnabled,
  });

  const platformsQuery = useQuery({
    queryKey: queryKeys.samplingPlatforms,
    queryFn: fetchSamplingPlatforms,
    ...sessionCatalogQueryOptions,
    enabled: catalogEnabled,
  });

  const platforms = useMemo(
    () => effectiveSamplingPlatforms(subject, platformsQuery.data ?? []),
    [subject.sampling_platforms, platformsQuery.data],
  );

  /** 全量平台目录，与 FilterBar / GET /sampling/platforms 同源，用于展示 label。 */
  const platformCatalog = platformsQuery.data ?? [];

  return {
    entities: entitiesQuery.data?.entities ?? [],
    topics: topicsQuery.data ?? [],
    platforms,
    platformCatalog,
    isLoading: entitiesQuery.isLoading || topicsQuery.isLoading || platformsQuery.isLoading,
  };
}
