import { useEffect, useState } from "react";

import { AnalysisFilterBar } from "@/components/analysis/common/AnalysisFilterBar";
import { TopicVisibilityRankTable } from "@/components/analysis/visibility/TopicVisibilityRankTable";
import { VisibilityMetricSection } from "@/components/analysis/visibility/VisibilityMetricSection";
import { useAnalysisOutletContext } from "@/hooks/useAnalysisContext";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { useVisibilityAnalysis } from "@/hooks/useVisibilityAnalysis";
import {
  ANALYSIS_DIMENSIONS,
  ANALYSIS_FILTER_ALL,
  DEFAULT_ANALYSIS_FILTERS,
} from "@/lib/analysis";
import { VISIBILITY_METRICS, VISIBILITY_SECTION_HEIGHT } from "@/lib/analysis/visibility";
import type { VisibilityMetricId } from "@/lib/analysis/visibility";
import type { AnalysisFilters } from "@/types";

const VISIBILITY_META = ANALYSIS_DIMENSIONS.find((d) => d.id === "visibility")!;

/** 可见度页布局：可见度 → AI 提及（各独占一行），声量份额 + 平均排名（并列一行） */
const VISIBILITY_LAYOUT: VisibilityMetricId[][] = [
  ["visibility"],
  ["mention"],
  ["shareVoice", "averageRank"],
];

export { VISIBILITY_SECTION_HEIGHT };

/** 分析 · 可见度 */
export function VisibilityPage() {
  const { subjectId } = useAnalysisOutletContext();
  const { subject } = useDashboardContext();

  const [filters, setFilters] = useState<AnalysisFilters>(DEFAULT_ANALYSIS_FILTERS);

  useEffect(() => {
    setFilters((prev) => ({
      ...prev,
      regionId: ANALYSIS_FILTER_ALL,
      topicId: ANALYSIS_FILTER_ALL,
      platformId: ANALYSIS_FILTER_ALL,
    }));
  }, [subject.id]);

  const { isLoading, ownLabel, topLabels, metrics, topicVisibilityRanks } = useVisibilityAnalysis(
    subjectId,
    filters,
  );

  return (
    <>
      <AnalysisFilterBar value={filters} onChange={setFilters} />
      <div className="flex flex-col gap-4 px-6 py-4">
        <header>
          <h2 className="text-xl font-semibold tracking-tight">{VISIBILITY_META.label}</h2>
          <p className="text-muted-foreground mt-1 max-w-3xl text-sm leading-relaxed">
            {VISIBILITY_META.description}
          </p>
        </header>

        <div className="flex flex-col gap-4">
          {VISIBILITY_LAYOUT.map((rowIds) => {
            const rowMetrics = rowIds
              .map((id) => VISIBILITY_METRICS.find((m) => m.id === id))
              .filter((m): m is NonNullable<typeof m> => m != null);

            const isPairRow = rowMetrics.length > 1;

            return (
              <div
                key={rowIds.join("-")}
                className={isPairRow ? "grid gap-4 lg:grid-cols-2" : undefined}
              >
                {rowMetrics.map((definition) => (
                  <VisibilityMetricSection
                    key={definition.id}
                    definition={definition}
                    metric={metrics[definition.id]}
                    topLabels={topLabels}
                    ownLabel={ownLabel}
                    scopeKey={`${subjectId}:${definition.id}`}
                    loading={isLoading}
                  />
                ))}
              </div>
            );
          })}

          <TopicVisibilityRankTable
            rows={topicVisibilityRanks}
            ownLabel={ownLabel}
            loading={isLoading}
          />
        </div>
      </div>
    </>
  );
}
