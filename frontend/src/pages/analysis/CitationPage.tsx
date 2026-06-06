import { useEffect, useState } from "react";

import { AnalysisFilterBar } from "@/components/analysis/common/AnalysisFilterBar";
import { CitationDetailSection } from "@/components/analysis/citation/CitationDetailSection";
import { CitationOverviewSection } from "@/components/analysis/citation/CitationOverviewSection";
import { useAnalysisOutletContext } from "@/hooks/useAnalysisContext";
import { useCitationAnalysis } from "@/hooks/useCitationAnalysis";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { ANALYSIS_DIMENSIONS, ANALYSIS_FILTER_ALL, DEFAULT_ANALYSIS_FILTERS } from "@/lib/analysis";
import type { AnalysisFilters } from "@/types";

const CITATION_META = ANALYSIS_DIMENSIONS.find((d) => d.id === "citation")!;

/** 分析 · 引用率 */
export function CitationPage() {
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

  const { isLoading, overview, topLabels, ownLabel } = useCitationAnalysis(subjectId, filters);

  return (
    <>
      <AnalysisFilterBar value={filters} onChange={setFilters} />

      <div className="flex flex-col gap-4 px-6 py-4">
        <header>
          <h2 className="text-xl font-semibold tracking-tight">{CITATION_META.label}</h2>
          <p className="text-muted-foreground mt-1 max-w-3xl text-sm leading-relaxed">
            {CITATION_META.description}
          </p>
        </header>

        <CitationOverviewSection
          overview={overview}
          topLabels={topLabels}
          ownLabel={ownLabel}
          subjectScopeKey={`${subjectId}:citation`}
          loading={isLoading}
        />

        <CitationDetailSection
          domains={overview.domains}
          urls={overview.urls}
          loading={isLoading}
        />
      </div>
    </>
  );
}
