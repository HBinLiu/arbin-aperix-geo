import { useMemo } from "react";

import { AnalysisRankTable, AVERAGE_RANK_TABLE_SORT, type RankRow } from "@/components/analysis/common/AnalysisRankTable";
import { buildBrandRankIcon } from "@/components/analysis/common/BrandRankIcon";
import { MetricTrendCard } from "@/components/analysis/common/MetricTrendCard";
import { AverageRankBarChart } from "@/components/analysis/visibility/AverageRankBarChart";
import { ShareVoiceDonutChart } from "@/components/analysis/visibility/ShareVoiceDonutChart";
import { useVisibilityChartUI } from "@/hooks/useVisibilityChartUI";
import {
  VISIBILITY_RANK_TABLE_HEIGHT,
  VISIBILITY_SECTION_HEIGHT,
  type VisibilityMetricBundle,
  type VisibilityMetricDefinition,
} from "@/lib/analysis/visibility";

const sectionMinHeight = { minHeight: VISIBILITY_SECTION_HEIGHT };

function withRankIcons(rows: RankRow[]) {
  return rows.map((row) => ({ ...row, icon: buildBrandRankIcon(row.domain ?? "") }));
}

type VisibilityMetricSectionProps = {
  definition: VisibilityMetricDefinition;
  metric: VisibilityMetricBundle;
  topLabels: string[];
  ownLabel: string;
  scopeKey: string;
  loading: boolean;
};

/** 可见度页单指标区块：趋势图 + 排名表 */
export function VisibilityMetricSection({
  definition,
  metric,
  topLabels,
  ownLabel,
  scopeKey,
  loading,
}: VisibilityMetricSectionProps) {
  const isLineChart = definition.chartType === "line";
  const chartUi = useVisibilityChartUI(topLabels, ownLabel, scopeKey);
  const rankRows = useMemo(() => withRankIcons(metric.rankRows), [metric.rankRows]);

  const chart = useMemo(() => {
    const chartClassName = "min-h-[120px] w-full flex-1";
    if (definition.chartType === "donut") {
      return (
        <ShareVoiceDonutChart
          slices={metric.pieSlices ?? []}
          className={chartClassName}
        />
      );
    }
    if (definition.chartType === "bar") {
      return (
        <AverageRankBarChart
          series={metric.rankSeries}
          className={chartClassName}
        />
      );
    }
    return undefined;
  }, [definition.chartType, metric.pieSlices, metric.rankSeries]);

  return (
    <div
      className="border-border w-full overflow-hidden rounded-lg border bg-muted-background"
      aria-busy={loading}
      aria-label={loading ? definition.loadingAriaLabel : undefined}
    >
      <div className="@container flex flex-wrap items-stretch">
        <div
          className="flex min-h-0 min-w-[min(100%,480px)] flex-[3] flex-col p-5"
          style={sectionMinHeight}
        >
          <MetricTrendCard
            embedded
            loading={loading}
            className="flex min-h-0 flex-1 flex-col"
            title={definition.label}
            description={definition.description}
            value={
              metric.ownValue != null ? definition.formatValue(metric.ownValue) : undefined
            }
            delta={definition.formatDelta(metric.ownValue, metric.prevOwnValue)}
            chart={chart}
            multiSeries={isLineChart ? metric.series : undefined}
            labels={isLineChart ? chartUi.chartLabels : undefined}
            hiddenLegendKeys={isLineChart ? chartUi.hiddenLegendKeys : undefined}
            onToggleLegendKey={isLineChart ? chartUi.toggleLegendKey : undefined}
            previousSeries={isLineChart ? metric.previousSeries : undefined}
            showCurrentPeriod={isLineChart ? chartUi.showCurrentPeriod : undefined}
            onToggleCurrentPeriod={isLineChart ? chartUi.setShowCurrentPeriod : undefined}
            showPreviousPeriod={isLineChart ? chartUi.showPreviousPeriod : undefined}
            onTogglePreviousPeriod={isLineChart ? chartUi.setShowPreviousPeriod : undefined}
            showCompare={isLineChart ? chartUi.showCompare : undefined}
            onToggleCompare={isLineChart ? chartUi.handleToggleCompare : undefined}
            valueFormatter={definition.formatValue}
            yAxisMode={definition.yAxisMode}
          />
        </div>
        <div
          className="border-border flex min-w-[min(100%,240px)] flex-[2] flex-col overflow-hidden border-t p-3 @min-[720px]:border-t-0 @min-[720px]:border-l"
          style={sectionMinHeight}
        >
          <AnalysisRankTable
            embedded
            loading={loading}
            showMoreFooter
            height={VISIBILITY_RANK_TABLE_HEIGHT}
            className="min-h-0"
            title={`${definition.label}排名`}
            valueHeader={definition.rankValueHeader}
            rows={rankRows}
            emptyMessage="暂无数据"
            initialSort={definition.id === "averageRank" ? AVERAGE_RANK_TABLE_SORT : undefined}
            valueSortDefault={definition.id === "averageRank" ? "asc" : undefined}
          />
        </div>
      </div>
    </div>
  );
}
