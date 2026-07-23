import type { RankRow } from "@/components/analysis/common/AnalysisRankTable";
import { formatCount, formatCountDelta } from "@/lib/analysis/format";
import { resolvePlatformMeta } from "@/lib/analysis/shared";
import type { FanoutAnalysisData, FanoutPromptRow, SamplingPlatform } from "@/types";

export const FANOUT_SECTION_HEIGHT = 380;
export const FANOUT_RANK_TABLE_HEIGHT = FANOUT_SECTION_HEIGHT - 24;

export const FANOUT_CHART_DESCRIPTION =
  "衡量 AI 回答前而生成的执行子查询数量；扇出越高，通常反映检索策略更充分、覆盖面更广。";

export type FanoutOverviewData = {
  fanoutCount: number;
  fanoutPrevious: number;
  series: FanoutAnalysisData["series"];
  previousSeries: FanoutAnalysisData["previous_series"];
  chartLabels: string[];
  legendLabels: Record<string, string>;
  rankRows: RankRow[];
};

export function buildFanoutOverview(
  data: FanoutAnalysisData | undefined,
  platformCatalog: SamplingPlatform[],
): FanoutOverviewData {
  const labels = data?.labels ?? [];
  const legendLabels: Record<string, string> = {};
  for (const platformId of labels) {
    legendLabels[platformId] = resolvePlatformMeta(platformId, platformCatalog).label;
  }

  const rankRows: RankRow[] = (data?.rank_table ?? []).map((row) => {
    const meta = resolvePlatformMeta(row.id, platformCatalog);
    return {
      id: row.id,
      label: meta.label || row.label,
      value: formatCount(row.cur_value),
      valueNum: row.cur_value ?? undefined,
      delta: formatCountDelta(row.cur_value, row.pre_value),
      deltaSortNum:
        row.cur_value != null && row.pre_value != null ? row.cur_value - row.pre_value : null,
    };
  });

  return {
    fanoutCount: data?.fanout_count ?? 0,
    fanoutPrevious: data?.fanout_previous ?? 0,
    series: data?.series ?? [],
    previousSeries: data?.previous_series ?? [],
    chartLabels: labels,
    legendLabels,
    rankRows,
  };
}

export function platformDistributionSegments(
  platformCounts: Record<string, number>,
  platformCatalog: SamplingPlatform[],
): { id: string; label: string; count: number; ratio: number }[] {
  const total = Object.values(platformCounts).reduce((sum, value) => sum + value, 0);
  if (total <= 0) return [];
  return Object.entries(platformCounts)
    .filter(([, count]) => count > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([id, count]) => {
      const meta = resolvePlatformMeta(id, platformCatalog);
      return {
        id,
        label: meta.label,
        count,
        ratio: count / total,
      };
    });
}

export type { FanoutPromptRow };
