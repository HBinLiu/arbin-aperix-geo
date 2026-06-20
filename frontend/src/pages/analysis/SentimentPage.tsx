import { AnalysisFilterBar } from "@/components/analysis/common/AnalysisFilterBar";
import { SentimentOverviewSection } from "@/components/analysis/sentiment/SentimentOverviewSection";
import { SentimentResponsesSection } from "@/components/analysis/sentiment/SentimentResponsesSection";
import { useAnalysisOutletContext } from "@/hooks/useAnalysisContext";
import { useAnalysisFilter } from "@/hooks/useAnalysisFilter";
import { useAnalysisFiltersState } from "@/hooks/useAnalysisFiltersState";
import { useSentimentAnalysis } from "@/hooks/useSentimentAnalysis";
import { ANALYSIS_DIMENSIONS } from "@/lib/analysis";

const SENTIMENT_META = ANALYSIS_DIMENSIONS.find((d) => d.id === "sentiment")!;

/** 分析 · 情感倾向 */
export function SentimentPage() {
  const { subjectId } = useAnalysisOutletContext();
  const { filters, setFilters } = useAnalysisFiltersState();
  const { entities, platforms } = useAnalysisFilter();

  const { isLoading, overview } = useSentimentAnalysis(subjectId, filters, entities);

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

        <SentimentOverviewSection
          overview={overview}
          platformsMeta={platforms}
          loading={isLoading}
        />
        <SentimentResponsesSection
          subjectId={subjectId}
          filters={filters}
          platformsMeta={platforms}
        />
      </div>
    </>
  );
}
