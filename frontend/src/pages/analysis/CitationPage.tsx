import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";

import { AnalysisFilterBar } from "@/components/analysis/common/AnalysisFilterBar";
import { CitationDetailSection } from "@/components/analysis/citation/CitationDetailSection";
import { CitationOverviewSection } from "@/components/analysis/citation/CitationOverviewSection";
import { Input } from "@/components/ui/input";
import { useAnalysisOutletContext } from "@/hooks/useAnalysisContext";
import { useAnalysisFilter } from "@/hooks/useAnalysisFilter";
import { useAnalysisFiltersState } from "@/hooks/useAnalysisFiltersState";
import { useCitationAnalysis } from "@/hooks/useCitationAnalysis";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { ANALYSIS_DIMENSIONS, entityChartLabels, entityLegendLabels } from "@/lib/analysis";

const CITATION_META = ANALYSIS_DIMENSIONS.find((d) => d.id === "citation")!;

/** 分析 · 引用率 */
export function CitationPage() {
  const { subjectId } = useAnalysisOutletContext();
  const { filters, setFilters } = useAnalysisFiltersState();
  const { entities } = useAnalysisFilter();
  const { subject } = useDashboardContext();
  const chartLabels = useMemo(() => entityChartLabels(entities), [entities]);
  const legendLabels = useMemo(() => entityLegendLabels(entities), [entities]);
  const [linkSearch, setLinkSearch] = useState("");
  const [debouncedLinkSearch, setDebouncedLinkSearch] = useState("");

  useEffect(() => {
    setLinkSearch("");
    setDebouncedLinkSearch("");
  }, [subject.id]);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedLinkSearch(linkSearch), 300);
    return () => window.clearTimeout(timer);
  }, [linkSearch]);

  const { isLoading, overview, ownLabel } = useCitationAnalysis(
    subjectId,
    filters,
    entities,
  );

  return (
    <>
      <AnalysisFilterBar
        value={filters}
        onChange={setFilters}
        afterFilters={
          <div className="relative w-[min(100%,240px)]">
            <span className="pointer-events-none absolute inset-y-0 left-3.5 z-10 flex items-center">
              <Search className="text-muted-foreground size-3.5" aria-hidden />
            </span>
            <Input
              type="search"
              value={linkSearch}
              onChange={(event) => setLinkSearch(event.target.value)}
              placeholder="搜索引用链接"
              controlSize="sm"
              className="border-border h-9 w-full rounded-lg bg-muted-background pl-9 text-xs"
              aria-label="搜索引用链接"
            />
          </div>
        }
      />

      <div className="flex flex-col gap-4 px-6 py-4">
        <header>
          <h2 className="text-xl font-semibold tracking-tight">{CITATION_META.label}</h2>
          <p className="text-muted-foreground mt-1 max-w-4xl text-sm leading-relaxed">
            {CITATION_META.description}
          </p>
        </header>

        <CitationOverviewSection
          overview={overview}
          chartLabels={chartLabels}
          legendLabels={legendLabels}
          ownLabel={ownLabel}
          subjectScopeKey={`${subjectId}:citation`}
          loading={isLoading}
        />

        <CitationDetailSection
          subjectId={subjectId}
          filters={filters}
          ownLabel={ownLabel}
          ownBrand={subject.brand}
          citationSearch={debouncedLinkSearch}
        />
      </div>
    </>
  );
}
