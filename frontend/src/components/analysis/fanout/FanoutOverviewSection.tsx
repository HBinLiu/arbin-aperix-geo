import { useCallback, useEffect, useMemo, useState } from "react";

import { AnalysisRankTable } from "@/components/analysis/common/AnalysisRankTable";
import { MetricTrendCard } from "@/components/analysis/common/MetricTrendCard";
import { PlatformLogo } from "@/components/brand/PlatformLogo";
import {
  FANOUT_CHART_DESCRIPTION,
  FANOUT_RANK_TABLE_HEIGHT,
  FANOUT_SECTION_HEIGHT,
  type FanoutOverviewData,
} from "@/lib/analysis/fanout";
import { formatCount, formatCountDelta } from "@/lib/analysis/format";

type FanoutOverviewSectionProps = {
  overview: FanoutOverviewData;
  subjectScopeKey: string;
  loading?: boolean;
};

function useChartLegendToggle(scopeKey: string) {
  const [hiddenLegendKeys, setHiddenLegendKeys] = useState<Set<string>>(() => new Set());

  useEffect(() => {
    setHiddenLegendKeys(new Set());
  }, [scopeKey]);

  const toggleLegendKey = useCallback((key: string) => {
    setHiddenLegendKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  return { hiddenLegendKeys, toggleLegendKey };
}

/** 查询扇出概览：总量趋势 + 平台排名 */
export function FanoutOverviewSection({
  overview,
  subjectScopeKey,
  loading = false,
}: FanoutOverviewSectionProps) {
  const { hiddenLegendKeys, toggleLegendKey } = useChartLegendToggle(subjectScopeKey);

  const rankRowsWithIcons = useMemo(
    () =>
      overview.rankRows.map((row) => ({
        ...row,
        icon: (
          <PlatformLogo provider={row.id} label={row.label} className="size-6 rounded-md" />
        ),
      })),
    [overview.rankRows],
  );

  return (
    <div
      className="border-border w-full overflow-hidden rounded-lg border bg-muted-background"
      aria-busy={loading}
    >
      <div className="@container flex flex-wrap items-stretch">
        <div
          className="flex min-h-0 min-w-[min(100%,480px)] flex-[3] flex-col p-5"
          style={{ minHeight: FANOUT_SECTION_HEIGHT }}
        >
          <MetricTrendCard
            embedded
            loading={loading}
            className="flex min-h-0 flex-1 flex-col"
            title="查询扇出"
            description={FANOUT_CHART_DESCRIPTION}
            value={formatCount(overview.fanoutCount)}
            delta={formatCountDelta(overview.fanoutCount, overview.fanoutPrevious)}
            multiSeries={overview.series}
            labels={overview.chartLabels}
            legendLabels={overview.legendLabels}
            hiddenLegendKeys={hiddenLegendKeys}
            onToggleLegendKey={toggleLegendKey}
            valueFormatter={formatCount}
            yAxisMode="score"
          />
        </div>
        <div
          className="border-border flex min-w-[min(100%,240px)] flex-[2] flex-col overflow-hidden border-t p-3 @min-[720px]:border-t-0 @min-[720px]:border-l"
          style={{ minHeight: FANOUT_SECTION_HEIGHT }}
        >
          <AnalysisRankTable
            embedded
            loading={loading}
            height={FANOUT_RANK_TABLE_HEIGHT}
            className="min-h-0"
            title="查询扇出排名"
            valueHeader="问题数量"
            rows={rankRowsWithIcons}
            entityHeader="平台"
            showEntityHover={false}
            showDeltaColumn={false}
            emptyMessage="暂无平台扇出数据"
          />
        </div>
      </div>
    </div>
  );
}
