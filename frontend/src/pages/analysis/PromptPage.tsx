import { useQuery } from "@tanstack/react-query";

import { AnalysisDimensionView } from "@/components/analysis/AnalysisDimensionView";
import { useAnalysisDateRange } from "@/hooks/useAnalysisContext";
import { useAnalysisOutletContext } from "@/hooks/useAnalysisContext";
import { fetchPromptsPerformance } from "@/api/analysis";
import { formatRate } from "@/lib/analysis";
import { queryKeys } from "@/lib/queries";

/** 分析 · 提示词 */
export function PromptPage() {
  const { subjectId } = useAnalysisOutletContext();
  const { from, to } = useAnalysisDateRange();

  const promptsQuery = useQuery({
    queryKey: queryKeys.analysisPrompts(subjectId, from, to),
    queryFn: () => fetchPromptsPerformance(subjectId, from, to),
  });

  if (promptsQuery.isLoading) {
    return <div className="bg-muted h-72 animate-pulse rounded-lg" />;
  }

  const sorted = [...(promptsQuery.data ?? [])].sort(
    (a, b) => (b.visibility_rate ?? 0) - (a.visibility_rate ?? 0),
  );

  return (
    <AnalysisDimensionView
      dimension="prompt"
      valueFormatter={(v) => formatRate(v)}
      rankHeader="可见度"
      rankRows={sorted.slice(0, 10).map((p) => ({
        id: p.prompt_id,
        label: p.prompt_text.length > 40 ? `${p.prompt_text.slice(0, 40)}…` : p.prompt_text,
        value: formatRate(p.visibility_rate),
        delta: null,
      }))}
    />
  );
}
