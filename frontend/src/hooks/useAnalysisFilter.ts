import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchAnalysisEntities } from "@/api/analysis";
import { fetchSamplingPlatforms, fetchSubjectTopics } from "@/api/brand";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import {
  effectiveSamplingPlatforms,
} from "@/lib/brand";
import { queryKeys, sessionCatalogQueryOptions } from "@/lib/queries";

/** 分析页筛选项：实体目录、主题列表、主体已选平台。 */
export function useAnalysisFilter() {
  const { subject } = useDashboardContext();

  const entitiesQuery = useQuery({
    queryKey: queryKeys.analysisEntities(subject.id),
    queryFn: () => fetchAnalysisEntities(subject.id),
    ...sessionCatalogQueryOptions,
  });

  const topicsQuery = useQuery({
    queryKey: queryKeys.subjectTopics(subject.id),
    queryFn: () => fetchSubjectTopics(subject.id),
    ...sessionCatalogQueryOptions,
  });

  const platformsQuery = useQuery({
    queryKey: queryKeys.samplingPlatforms,
    queryFn: fetchSamplingPlatforms,
    ...sessionCatalogQueryOptions,
  });

  const platforms = useMemo(
    () => effectiveSamplingPlatforms(subject, platformsQuery.data ?? []),
    [subject.sampling_platforms, platformsQuery.data],
  );

  return {
    entities: entitiesQuery.data?.entities ?? [],
    topics: topicsQuery.data ?? [],
    platforms,
    isLoading: entitiesQuery.isLoading || topicsQuery.isLoading || platformsQuery.isLoading,
  };
}
