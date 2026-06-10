import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { AnalysisFilterBar } from "@/components/analysis/common/AnalysisFilterBar";
import { SimpleLineChart } from "@/components/analysis/common/SimpleLineChart";
import {
  PromptDetailMetricCards,
  promptDetailMetricCardValues,
} from "@/components/analysis/prompt/PromptDetailMetricCards";
import { PromptDetailOpportunity } from "@/components/analysis/prompt/PromptDetailOpportunity";
import { PromptDetailResponsesSection } from "@/components/analysis/prompt/PromptDetailResponsesSection";
import { PromptPlatformBarChart } from "@/components/analysis/prompt/PromptPlatformBarChart";
import { useAnalysisFilter } from "@/hooks/useAnalysisFilter";
import { useAnalysisOutletContext } from "@/hooks/useAnalysisContext";
import { usePromptDetailAnalysis, usePromptDetailMeta } from "@/hooks/usePromptDetailAnalysis";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { ANALYSIS_FILTER_ALL, DEFAULT_ANALYSIS_FILTERS } from "@/lib/analysis";
import {
  promptDetailMetric,
  type PromptDetailMetricId,
} from "@/lib/analysis/promptDetail";
import type { AnalysisFilters } from "@/types";

const CHART_HEIGHT = 270;

function decodeRoutePromptId(value: string | undefined): string {
  if (!value) return "";
  try {
    return decodeURIComponent(value).trim();
  } catch {
    return value.trim();
  }
}

/** 分析 · 提示词 · 单条详情 */
export function PromptDetailPage() {
  const { promptId: promptIdParam } = useParams<{ promptId: string }>();
  const promptId = decodeRoutePromptId(promptIdParam);
  const { subjectId } = useAnalysisOutletContext();
  const { subject } = useDashboardContext();
  const { platforms: platformsMeta } = useAnalysisFilter();

  const [filters, setFilters] = useState<AnalysisFilters>(DEFAULT_ANALYSIS_FILTERS);
  const [activeMetricId, setActiveMetricId] = useState<PromptDetailMetricId>("visibility");

  useEffect(() => {
    setFilters((prev) => ({
      ...prev,
      regionId: ANALYSIS_FILTER_ALL,
      topicId: ANALYSIS_FILTER_ALL,
      platformId: ANALYSIS_FILTER_ALL,
    }));
  }, [subject.id]);

  const { isLoading, summary, platforms, lineSeriesByMetric, opportunity, ownLabel, responses, responsesLoading } =
    usePromptDetailAnalysis(subjectId, promptId, filters);
  const { promptText } = usePromptDetailMeta(subjectId, promptId);

  const activeMetric = promptDetailMetric(activeMetricId);
  const cardValues = useMemo(
    () => promptDetailMetricCardValues(summary.current),
    [summary.current],
  );
  const lineSeries = lineSeriesByMetric[activeMetricId];

  return (
    <>
      <AnalysisFilterBar value={filters} onChange={setFilters} />

      <div className="flex flex-col gap-4 px-6 py-4">
        <PromptDetailMetricCards
          activeMetricId={activeMetricId}
          onMetricChange={setActiveMetricId}
          values={cardValues}
          loading={isLoading}
        />

        <section className="border-border overflow-hidden rounded-lg border bg-white">
          <div className="border-border border-b px-5 py-4">
            <p className="text-muted-foreground text-sm leading-relaxed">
              {activeMetric.chartDescription}
            </p>
          </div>
          <div className="grid gap-0 lg:grid-cols-2">
            <div className="border-border p-5 lg:border-r">
              <h4 className="mb-4 text-sm font-semibold">{activeMetric.label}</h4>
              <SimpleLineChart
                singleSeries={lineSeries}
                labels={ownLabel ? [ownLabel] : []}
                showPreviousSeries={false}
                valueFormatter={(value) => activeMetric.formatValue(value)}
                yAxisMode={activeMetric.yAxisMode}
                height={CHART_HEIGHT}
              />
            </div>
            <div className="p-5">
              <h4 className="mb-4 text-sm font-semibold">按平台</h4>
              <PromptPlatformBarChart
                platforms={platforms}
                platformsMeta={platformsMeta}
                metricId={activeMetricId}
                height={CHART_HEIGHT}
              />
            </div>
          </div>
        </section>

        <PromptDetailOpportunity opportunity={opportunity} loading={isLoading} />

        <PromptDetailResponsesSection
          data={responses}
          platformsMeta={platformsMeta}
          promptText={promptText}
          loading={responsesLoading}
        />
      </div>
    </>
  );
}
