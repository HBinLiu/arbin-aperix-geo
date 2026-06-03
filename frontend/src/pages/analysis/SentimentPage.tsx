import { useQuery } from "@tanstack/react-query";

import { AnalysisDimensionView } from "@/components/analysis/AnalysisDimensionView";
import { useAnalysisDateRange } from "@/hooks/useAnalysisContext";
import { useAnalysisOutletContext } from "@/hooks/useAnalysisContext";
import { fetchDailySentiment, fetchRank } from "@/api/analysis";
import { buildBrandRankRows, formatRate, formatScore } from "@/lib/analysis";
import { queryKeys } from "@/lib/queries";

/** 分析 · 情感倾向 */
export function SentimentPage() {
  const { subjectId } = useAnalysisOutletContext();
  const { from, to } = useAnalysisDateRange();

  const rankQuery = useQuery({
    queryKey: queryKeys.analysisRank(subjectId, from, to),
    queryFn: () => fetchRank(subjectId, from, to),
  });

  const dailyQuery = useQuery({
    queryKey: queryKeys.analysisDailySentiment(subjectId, from, to),
    queryFn: () => fetchDailySentiment(subjectId, from, to),
  });

  if (rankQuery.isLoading || dailyQuery.isLoading) {
    return <div className="bg-muted h-72 animate-pulse rounded-lg" />;
  }

  const rank = rankQuery.data;
  const ownLabel = rank?.own_label ?? dailyQuery.data?.own_label ?? "";

  return (
    <AnalysisDimensionView
      dimension="sentiment"
      singleSeries={dailyQuery.data?.series.map((p) => ({ date: p.date, value: p.value }))}
      valueFormatter={(v) => formatScore(v)}
      rankHeader="可见度"
      rankRows={
        rank
          ? buildBrandRankRows(rank.visibility_share, undefined, ownLabel, (v) => formatRate(v))
          : []
      }
    />
  );
}
