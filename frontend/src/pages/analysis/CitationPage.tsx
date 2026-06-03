import { useQuery } from "@tanstack/react-query";

import { AnalysisDimensionView } from "@/components/analysis/AnalysisDimensionView";
import { useAnalysisDateRange } from "@/hooks/useAnalysisContext";
import { useAnalysisOutletContext } from "@/hooks/useAnalysisContext";
import { fetchCitationRank } from "@/api/analysis";
import { buildBrandRankRows, formatRate } from "@/lib/analysis";
import { queryKeys } from "@/lib/queries";

/** 分析 · 引用率 */
export function CitationPage() {
  const { subjectId } = useAnalysisOutletContext();
  const { from, to } = useAnalysisDateRange();

  const citationRankQuery = useQuery({
    queryKey: queryKeys.analysisCitationRank(subjectId, from, to),
    queryFn: () => fetchCitationRank(subjectId, from, to),
  });

  if (citationRankQuery.isLoading) {
    return <div className="bg-muted h-72 animate-pulse rounded-lg" />;
  }

  const citationRank = citationRankQuery.data;
  const ownLabel = citationRank?.own_label ?? "";

  return (
    <AnalysisDimensionView
      dimension="citation"
      valueFormatter={(v) => formatRate(v)}
      rankHeader="引用率"
      rankRows={
        citationRank
          ? buildBrandRankRows(citationRank.citation_share, undefined, ownLabel, (v) => formatRate(v))
          : []
      }
    />
  );
}
