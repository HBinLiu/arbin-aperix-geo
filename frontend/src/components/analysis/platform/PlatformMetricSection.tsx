import { AnalysisRankTable } from "@/components/analysis/common/AnalysisRankTable";
import type { RankRow } from "@/components/analysis/common/AnalysisRankTable";
import { MetricTrendCard } from "@/components/analysis/common/MetricTrendCard";
import { SimpleLineChart } from "@/components/analysis/common/SimpleLineChart";
import { PlatformLogo } from "@/components/brand/PlatformLogo";
import type { PlatformMatrixMetricDefinition } from "@/lib/analysis/platform";
import { resolvePlatformMeta } from "@/lib/analysis/shared";
import type { PlatformMatrixSeriesPoint, SamplingPlatform } from "@/types";
import { useMemo } from "react";

const SECTION_HEIGHT = 380;
const CHART_HEIGHT = 270;
const RANK_TABLE_HEIGHT = SECTION_HEIGHT - 24;

type PlatformMetricSectionProps = {
  metric: PlatformMatrixMetricDefinition;
  selectedPlatformId: string | null;
  platformsMeta: SamplingPlatform[];
  value: number | null | undefined;
  series: PlatformMatrixSeriesPoint[];
  rankRows: RankRow[];
  loading?: boolean;
};

export function PlatformMetricSection({
  metric,
  selectedPlatformId,
  platformsMeta,
  value,
  series,
  rankRows,
  loading = false,
}: PlatformMetricSectionProps) {
  const platformLabel = selectedPlatformId
    ? resolvePlatformMeta(selectedPlatformId, platformsMeta).label
    : "";

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
      className="border-border w-full overflow-hidden rounded-lg border bg-white"
      aria-busy={loading}
    >
      <div className="@container flex flex-wrap items-stretch">
        <div
          className="flex min-w-[min(100%,480px)] flex-[3] flex-col p-5"
          style={{ minHeight: SECTION_HEIGHT }}
        >
          <MetricTrendCard
            embedded
            loading={loading}
            chartHeight={CHART_HEIGHT}
            className="flex flex-col"
            title={metric.label}
            description={`${platformLabel || "所选平台"}的${metric.label}趋势`}
            value={value != null ? metric.formatValue(value) : undefined}
            showValueDelta={false}
            valueFormatter={(v) => metric.formatValue(v)}
            yAxisMode={metric.yAxisMode}
            chart={
              selectedPlatformId ? (
                <SimpleLineChart
                  singleSeries={series.map((point) => ({ date: point.date, value: point.value }))}
                  labels={[platformLabel]}
                  showPreviousSeries={false}
                  valueFormatter={(v) => metric.formatValue(v)}
                  yAxisMode={metric.yAxisMode}
                  height={CHART_HEIGHT}
                  className="mt-4 w-full"
                />
              ) : undefined
            }
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
            emptyMessage="暂无平台排名数据"
          />
        </div>
      </div>
    </div>
  );
}

export { SECTION_HEIGHT as PLATFORM_SECTION_HEIGHT };
