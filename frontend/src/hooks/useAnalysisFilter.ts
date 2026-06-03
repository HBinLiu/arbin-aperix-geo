import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchSamplingPlatforms, fetchSubjectTopics } from "@/api/brand";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import {
  effectiveSamplingPlatforms,
} from "@/lib/brand";
import { queryKeys } from "@/lib/queries";

/** 分析页筛选项：主题列表 + 主体已选平台。 */
export function useAnalysisFilter() {
  const { subject } = useDashboardContext();

  const topicsQuery = useQuery({
    queryKey: queryKeys.subjectTopics(subject.id),
    queryFn: () => fetchSubjectTopics(subject.id),
  });

  const platformsQuery = useQuery({
    queryKey: queryKeys.samplingPlatforms,
    queryFn: fetchSamplingPlatforms,
  });

  const platforms = useMemo(
    () => effectiveSamplingPlatforms(subject, platformsQuery.data ?? []),
    [subject.sampling_platforms, platformsQuery.data],
  );

  return {
    topics: topicsQuery.data ?? [],
    platforms,
    isLoading: topicsQuery.isLoading || platformsQuery.isLoading,
  };
}
