import { useQuery } from "@tanstack/react-query";

import { AnalysisDimensionView } from "@/components/analysis/AnalysisDimensionView";
import { useAnalysisDateRange } from "@/hooks/useAnalysisContext";
import { useAnalysisOutletContext } from "@/hooks/useAnalysisContext";
import { formatRate, resolvePlatformMeta } from "@/lib/analysis";
import { PlatformLogo } from "@/components/brand/PlatformLogo";
import { fetchPlatformPerformance } from "@/api/analysis";
import { fetchSamplingPlatforms } from "@/api/brand";
import { queryKeys } from "@/lib/queries";

/** 分析 · AI 平台 */
export function PlatformPage() {
  const { subjectId } = useAnalysisOutletContext();
  const { from, to } = useAnalysisDateRange();

  const platformsQuery = useQuery({
    queryKey: queryKeys.analysisPlatforms(subjectId, from, to),
    queryFn: () => fetchPlatformPerformance(subjectId, from, to),
  });

  const platformsMetaQuery = useQuery({
    queryKey: queryKeys.samplingPlatforms,
    queryFn: fetchSamplingPlatforms,
  });

  if (platformsQuery.isLoading || platformsMetaQuery.isLoading) {
    return <div className="bg-muted h-72 animate-pulse rounded-lg" />;
  }

  const platformsMeta = platformsMetaQuery.data ?? [];
  const sorted = [...(platformsQuery.data ?? [])].sort(
    (a, b) => (b.visibility_rate ?? 0) - (a.visibility_rate ?? 0),
  );

  return (
    <AnalysisDimensionView
      dimension="platform"
      valueFormatter={(v) => formatRate(v)}
      rankHeader="可见度"
      rankRows={sorted.map((p) => {
        const meta = resolvePlatformMeta(p.platform, platformsMeta);
        return {
          id: p.platform,
          label: meta.label,
          value: formatRate(p.visibility_rate),
          delta: null,
          icon: (
            <PlatformLogo provider={meta.platform} label={meta.label} className="size-7 rounded-md" />
          ),
        };
      })}
    />
  );
}
