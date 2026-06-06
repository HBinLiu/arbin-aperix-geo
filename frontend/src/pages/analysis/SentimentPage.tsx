import { useEffect, useMemo, useState } from "react";

import { AnalysisFilterBar } from "@/components/analysis/common/AnalysisFilterBar";
import { SentimentOverviewSection } from "@/components/analysis/sentiment/SentimentOverviewSection";
import { SentimentResponsesSection } from "@/components/analysis/sentiment/SentimentResponsesSection";
import { useAnalysisOutletContext } from "@/hooks/useAnalysisContext";
import { useAnalysisFilter } from "@/hooks/useAnalysisFilter";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { useSentimentAnalysis } from "@/hooks/useSentimentAnalysis";
import { ANALYSIS_DIMENSIONS, ANALYSIS_FILTER_ALL, DEFAULT_ANALYSIS_FILTERS } from "@/lib/analysis";
import type { AnalysisFilters } from "@/types";

const SENTIMENT_META = ANALYSIS_DIMENSIONS.find((d) => d.id === "sentiment")!;

/** 分析 · 情感倾向 */
export function SentimentPage() {
  const { subjectId } = useAnalysisOutletContext();
  const { subject } = useDashboardContext();
  const { platforms } = useAnalysisFilter();

  const [filters, setFilters] = useState<AnalysisFilters>(DEFAULT_ANALYSIS_FILTERS);

  useEffect(() => {
    setFilters((prev) => ({
      ...prev,
      regionId: ANALYSIS_FILTER_ALL,
      topicId: ANALYSIS_FILTER_ALL,
      platformId: ANALYSIS_FILTER_ALL,
    }));
  }, [subject.id]);

  const { isLoading, overview } = useSentimentAnalysis(subjectId, filters);

  const platformsMeta = useMemo(() => platforms, [platforms]);

  return (
    <>
      <AnalysisFilterBar value={filters} onChange={setFilters} />

      <div className="flex flex-col gap-4 px-6 py-4">
        <header>
          <h2 className="text-xl font-semibold tracking-tight">{SENTIMENT_META.label}</h2>
          <p className="text-muted-foreground mt-1 max-w-3xl text-sm leading-relaxed">
            {SENTIMENT_META.description}
          </p>
        </header>

        <SentimentOverviewSection overview={overview} loading={isLoading} />
        <SentimentResponsesSection
          responses={overview.responses}
          platformsMeta={platformsMeta}
          loading={isLoading}
        />
      </div>
    </>
  );
}
