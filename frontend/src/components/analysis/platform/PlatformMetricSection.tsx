import { useCallback, useEffect, useMemo, useState } from "react";

import { AnalysisRankTable } from "@/components/analysis/common/AnalysisRankTable";
import type { RankRow } from "@/components/analysis/common/AnalysisRankTable";
import { MetricTrendCard } from "@/components/analysis/common/MetricTrendCard";
import { PlatformLogo } from "@/components/brand/PlatformLogo";
import type { MultiSeriesPoint } from "@/lib/analysis/chart";
import { platformMatrixMetricDescription, type PlatformMatrixMetricDefinition } from "@/lib/analysis/platform";

const SECTION_HEIGHT = 380;
const RANK_TABLE_HEIGHT = SECTION_HEIGHT - 24;

type PlatformMetricSectionProps = {
  metric: PlatformMatrixMetricDefinition;
  multiSeries: MultiSeriesPoint[];
  chartLabels: string[];
  scopeKey: string;
  rankRows: RankRow[];
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

export function PlatformMetricSection({
  metric,
  multiSeries,
  chartLabels,
  scopeKey,
  rankRows,
  loading = false,
}: PlatformMetricSectionProps) {
  const { hiddenLegendKeys, toggleLegendKey } = useChartLegendToggle(scopeKey);

  const rankRowsWithIcons = useMemo(
    () =>
      rankRows.map((row) => ({
        ...row,
        icon: (
          <PlatformLogo
            provider={row.id}
            label={row.label}
            className="size-6 rounded-md"
          />
        ),
      })),
    [rankRows],
  );

  return (
    <div
      className="border-border w-full overflow-hidden rounded-lg border bg-muted-background"
      aria-busy={loading}
    >
      <div className="@container flex flex-wrap items-stretch">
        <div
          className="flex min-h-0 min-w-[min(100%,480px)] flex-[3] flex-col p-5"
          style={{ minHeight: SECTION_HEIGHT }}
        >
          <MetricTrendCard
            embedded
            loading={loading}
            className="flex min-h-0 flex-1 flex-col"
            title={metric.label}
            description={platformMatrixMetricDescription(metric.label)}
            showValue={false}
            multiSeries={multiSeries}
            labels={chartLabels}
            hiddenLegendKeys={hiddenLegendKeys}
            onToggleLegendKey={toggleLegendKey}
            valueFormatter={(v) => metric.formatValue(v)}
            yAxisMode={metric.yAxisMode}
          />
        </div>
        <div
          className="border-border flex min-w-[min(100%,240px)] flex-[2] flex-col overflow-hidden border-t p-3 @min-[720px]:border-t-0 @min-[720px]:border-l"
          style={{ minHeight: SECTION_HEIGHT }}
        >
          <AnalysisRankTable
            embedded
            loading={loading}
            height={RANK_TABLE_HEIGHT}
            className="min-h-0"
            title={`${metric.label}排名`}
            valueHeader={metric.rankHeader}
            rows={rankRowsWithIcons}
            entityHeader="平台"
            showEntityHover={false}
            emptyMessage="暂无平台排名数据"
          />
        </div>
      </div>
    </div>
  );
}

export { SECTION_HEIGHT as PLATFORM_SECTION_HEIGHT };
