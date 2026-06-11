import { useEffect, useState } from "react";

import { AnalysisFilterBar } from "@/components/analysis/common/AnalysisFilterBar";
import { PlatformMatrixConfig } from "@/components/analysis/platform/PlatformMatrixConfig";
import { PlatformMatrixTable } from "@/components/analysis/platform/PlatformMatrixTable";
import { PlatformMetricSection } from "@/components/analysis/platform/PlatformMetricSection";
import { useAnalysisOutletContext } from "@/hooks/useAnalysisContext";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { usePlatformAnalysis } from "@/hooks/usePlatformAnalysis";
import { ANALYSIS_FILTER_ALL, DEFAULT_ANALYSIS_FILTERS } from "@/lib/analysis";
import {
  PLATFORM_METRIC_LAYOUT,
  PLATFORM_PAGE_DESCRIPTION,
  PLATFORM_PAGE_TITLE,
  PLATFORM_MATRIX_METRICS,
} from "@/lib/analysis/platform";
import type { AnalysisFilters, PlatformMatrixMetricId, PlatformMatrixRowDimension } from "@/types";

/** 分析 · 平台可见度矩阵 */
export function PlatformPage() {
  const { subjectId } = useAnalysisOutletContext();
  const { subject } = useDashboardContext();

  const [filters, setFilters] = useState<AnalysisFilters>(DEFAULT_ANALYSIS_FILTERS);
  const [rowDimension, setRowDimension] = useState<PlatformMatrixRowDimension>("competitor");
  const [metricId, setMetricId] = useState<PlatformMatrixMetricId>("visibility");
  const [selectedPlatformId, setSelectedPlatformId] = useState<string | null>(null);

  useEffect(() => {
    setFilters((prev) => ({
      ...prev,
      regionId: ANALYSIS_FILTER_ALL,
      topicId: ANALYSIS_FILTER_ALL,
      platformId: ANALYSIS_FILTER_ALL,
    }));
    setSelectedPlatformId(null);
  }, [subject.id]);

  const {
    isLoading,
    data,
    platformsMeta,
    metric,
    matrixRows,
    platformMetrics,
  } = usePlatformAnalysis(subjectId, filters, rowDimension, metricId, selectedPlatformId);

  const platforms = data?.platforms ?? [];

  useEffect(() => {
    if (platforms.length === 0) {
      setSelectedPlatformId(null);
      return;
    }
    const filteredPlatform =
      filters.platformId !== ANALYSIS_FILTER_ALL ? filters.platformId : null;
    if (filteredPlatform && platforms.includes(filteredPlatform)) {
      setSelectedPlatformId(filteredPlatform);
      return;
    }
    if (!selectedPlatformId || !platforms.includes(selectedPlatformId)) {
      setSelectedPlatformId(platforms[0]);
    }
  }, [platforms, selectedPlatformId, filters.platformId]);

  return (
    <>
      <AnalysisFilterBar value={filters} onChange={setFilters} hideEntityFilter hidePlatformFilter />
      <div className="flex flex-col gap-4 px-6 py-4">
        <header className="flex flex-wrap items-center justify-between gap-x-4 gap-y-3">
          <div className="min-w-0 flex-1">
            <h2 className="text-xl font-semibold tracking-tight">{PLATFORM_PAGE_TITLE}</h2>
            <p className="text-muted-foreground mt-1 max-w-3xl text-sm leading-relaxed">
              {PLATFORM_PAGE_DESCRIPTION}
            </p>
          </div>
          <div className="shrink-0">
            <PlatformMatrixConfig
              rowDimension={rowDimension}
              metricId={metricId}
              onRowDimensionChange={setRowDimension}
              onMetricChange={setMetricId}
            />
          </div>
        </header>

        <PlatformMatrixTable
          rowDimension={rowDimension}
          metric={metric}
          rows={matrixRows}
          platforms={platforms}
          platformsMeta={platformsMeta}
          onSelectPlatform={setSelectedPlatformId}
          loading={isLoading}
        />

        <div className="flex flex-col gap-4">
          {PLATFORM_METRIC_LAYOUT.map((rowIds) => {
            const rowMetrics = rowIds
              .map((id) => PLATFORM_MATRIX_METRICS.find((m) => m.id === id))
              .filter((m): m is NonNullable<typeof m> => m != null);

            const isPairRow = rowMetrics.length > 1;

            return (
              <div
                key={rowIds.join("-")}
                className={isPairRow ? "grid gap-4 lg:grid-cols-2" : undefined}
              >
                {rowMetrics.map((definition) => {
                  const bundle = platformMetrics[definition.id];
                  return (
                    <PlatformMetricSection
                      key={definition.id}
                      metric={definition}
                      selectedPlatformId={selectedPlatformId}
                      platformsMeta={platformsMeta}
                      value={bundle.value}
                      series={bundle.series}
                      rankRows={bundle.rankRows}
                      loading={isLoading}
                    />
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}
