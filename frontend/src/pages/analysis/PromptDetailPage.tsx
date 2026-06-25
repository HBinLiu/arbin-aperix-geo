import { useState } from "react";
import { useParams } from "react-router-dom";

import { AnalysisFilterBar } from "@/components/analysis/common/AnalysisFilterBar";
import { SimpleLineChart } from "@/components/analysis/common/SimpleLineChart";
import {
  PromptDetailMetricCards,
} from "@/components/analysis/prompt/PromptDetailMetricCards";
import { PromptDetailOpportunity } from "@/components/analysis/prompt/PromptDetailOpportunity";
import { PromptDetailResponsesSection } from "@/components/analysis/prompt/PromptDetailResponsesSection";
import { PromptPlatformBarChart } from "@/components/analysis/prompt/PromptPlatformBarChart";
import { useAnalysisOutletContext } from "@/hooks/useAnalysisContext";
import { useAnalysisFiltersState } from "@/hooks/useAnalysisFiltersState";
import { usePromptDetailAnalysis } from "@/hooks/usePromptDetailAnalysis";
import {
  promptDetailMetric,
  type PromptDetailMetricId,
} from "@/lib/analysis/promptDetail";

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
  const { filters, setFilters } = useAnalysisFiltersState();
  const [activeMetricId, setActiveMetricId] = useState<PromptDetailMetricId>("visibility");

  const {
    isLoading,
    cardValues,
    platforms,
    lineSeriesByMetric,
    opportunity,
    responses,
  } = usePromptDetailAnalysis(subjectId, promptId, filters);

  const activeMetric = promptDetailMetric(activeMetricId);
  const lineSeries = lineSeriesByMetric[activeMetricId];

  return (
    <>
      <AnalysisFilterBar value={filters} onChange={setFilters} hideTopicFilter />

      <div className="flex flex-col gap-4 px-6 py-4">
        <PromptDetailMetricCards
          activeMetricId={activeMetricId}
          onMetricChange={setActiveMetricId}
          values={cardValues}
          loading={isLoading}
        />

        <section className="border-border overflow-hidden rounded-lg border bg-white">
          <div className="border-border bg-muted border-b px-5 py-3">
            <p className="text-muted-foreground text-sm font-medium leading-relaxed">
              {activeMetric.chartDescription}
            </p>
          </div>
          <div className="grid gap-0 lg:grid-cols-2">
            <div className="border-border p-5 lg:border-r">
              <h4 className="mb-4 text-sm font-semibold">{activeMetric.label}</h4>
              <SimpleLineChart
                singleSeries={lineSeries}
                labels={responses?.entity_label ? [responses.entity_label] : []}
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
                metricId={activeMetricId}
                height={CHART_HEIGHT}
              />
            </div>
          </div>
        </section>

        <PromptDetailOpportunity opportunity={opportunity} loading={isLoading} />

        <PromptDetailResponsesSection
          subjectId={subjectId}
          promptId={promptId}
          filters={filters}
          data={responses}
          detailLoading={isLoading}
        />
      </div>
    </>
  );
}
