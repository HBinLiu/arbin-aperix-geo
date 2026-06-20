import { useMemo } from "react";

import { AnalysisRankTable, type RankRow } from "@/components/analysis/common/AnalysisRankTable";
import { buildBrandRankIcon } from "@/components/analysis/common/BrandRankIcon";
import { MetricTrendCard } from "@/components/analysis/common/MetricTrendCard";
import { useVisibilityChartUI } from "@/hooks/useVisibilityChartUI";
import {
  CITATION_CHART_DESCRIPTION,
  CITATION_RANK_TABLE_HEIGHT,
  CITATION_SECTION_HEIGHT,
  type CitationOverviewData,
} from "@/lib/analysis/citation";
import { formatDelta, formatRate } from "@/lib/analysis/format";

function withRankIcons(rows: RankRow[]) {
  return rows.map((row) => ({ ...row, icon: buildBrandRankIcon(row.domain ?? "") }));
}

type CitationOverviewSectionProps = {
  overview: CitationOverviewData;
  chartLabels: string[];
  ownLabel: string;
  subjectScopeKey: string;
  loading?: boolean;
};

export function CitationOverviewSection({
  overview,
  chartLabels,
  ownLabel,
  subjectScopeKey,
  loading = false,
}: CitationOverviewSectionProps) {
  const chartUi = useVisibilityChartUI(chartLabels, ownLabel, subjectScopeKey);
  const rankRows = useMemo(() => withRankIcons(overview.rankRows), [overview.rankRows]);

  return (
    <div
      className="border-border w-full overflow-hidden rounded-lg border bg-white"
      aria-busy={loading}
    >
      <div className="@container flex flex-wrap items-stretch">
        <div
          className="flex min-h-0 min-w-[min(100%,480px)] flex-[3] flex-col p-5"
          style={{ minHeight: CITATION_SECTION_HEIGHT }}
        >
          <MetricTrendCard
            embedded
            loading={loading}
            className="flex min-h-0 flex-1 flex-col"
            title="引用率"
            description={CITATION_CHART_DESCRIPTION}
            value={overview.ownValue != null ? formatRate(overview.ownValue) : undefined}
            delta={formatDelta(overview.ownValue, overview.prevOwnValue)}
            multiSeries={overview.series}
            labels={chartUi.chartLabels}
            hiddenLegendKeys={chartUi.hiddenLegendKeys}
            onToggleLegendKey={chartUi.toggleLegendKey}
            previousSeries={overview.previousSeries}
            showCurrentPeriod={chartUi.showCurrentPeriod}
            onToggleCurrentPeriod={chartUi.setShowCurrentPeriod}
            showPreviousPeriod={chartUi.showPreviousPeriod}
            onTogglePreviousPeriod={chartUi.setShowPreviousPeriod}
            showCompare={chartUi.showCompare}
            onToggleCompare={chartUi.handleToggleCompare}
            valueFormatter={formatRate}
            yAxisMode="rate"
          />
        </div>
        <div
          className="border-border flex min-w-[min(100%,240px)] flex-[2] flex-col overflow-hidden border-t p-3 @min-[720px]:border-t-0 @min-[720px]:border-l"
          style={{ minHeight: CITATION_SECTION_HEIGHT }}
        >
          <AnalysisRankTable
            embedded
            loading={loading}
            showMoreFooter
            height={CITATION_RANK_TABLE_HEIGHT}
            className="min-h-0"
            title="引用率排名"
            valueHeader="引用率"
            rows={rankRows}
            emptyMessage="暂无排名数据"
          />
        </div>
      </div>
    </div>
  );
}
