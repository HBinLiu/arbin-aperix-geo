import type { RankRow } from "@/components/analysis/common/AnalysisRankTable";
import type { ShareVoiceSlice } from "@/components/analysis/visibility/ShareVoiceDonutChart";
import {
  formatDelta,
  formatRate,
  formatRankMetric,
  formatScoreDelta,
} from "@/lib/analysis/format";
import { ANALYSIS_DIMENSIONS } from "@/lib/analysis/nav";
import { buildBrandRankRows } from "@/lib/analysis/shared";
import type { SingleSeriesPoint } from "@/lib/analysis/chart";
import type { VisibilityAnalysisData, VisibilitySeriesPoint } from "@/types";

/** 可见度页折线图展示模式 */
export type VisibilityChartMode = "competitors" | "own" | "own-with-previous";

export function resolveVisibilityChartMode(
  showCompare: boolean,
  showPreviousPeriod: boolean,
): VisibilityChartMode {
  if (showCompare) return "competitors";
  if (showPreviousPeriod) return "own-with-previous";
  return "own";
}

export function visibilityChartLabels(
  mode: VisibilityChartMode,
  topLabels: string[],
  ownLabel: string,
): string[] {
  if (mode === "competitors") return topLabels;
  return ownLabel ? [ownLabel] : [];
}

export const VISIBILITY_SECTION_HEIGHT = 380;
export const VISIBILITY_CHART_HEIGHT = 270;
export const VISIBILITY_RANK_TABLE_HEIGHT = VISIBILITY_SECTION_HEIGHT - 24;

export type VisibilityMetricId = "visibility" | "mention" | "shareVoice" | "averageRank";

export type VisibilityChartType = "line" | "donut" | "bar";

export type VisibilityMetricBundle = {
  series?: VisibilitySeriesPoint[];
  previousSeries?: VisibilitySeriesPoint[];
  rankSeries?: SingleSeriesPoint[];
  pieSlices?: ShareVoiceSlice[];
  ownValue?: number;
  prevOwnValue?: number;
  rankRows: RankRow[];
};

export type VisibilityMetricDefinition = {
  id: VisibilityMetricId;
  label: string;
  description: string;
  rankValueHeader: string;
  loadingAriaLabel: string;
  chartType: VisibilityChartType;
  formatValue: (v: number | null | undefined) => string;
  formatDelta: (
    current: number | null | undefined,
    previous: number | null | undefined,
  ) => string | null;
  yAxisMode?: "rate" | "score";
};

const VISIBILITY_META = ANALYSIS_DIMENSIONS.find((d) => d.id === "visibility")!;

export const VISIBILITY_METRICS: VisibilityMetricDefinition[] = [
  {
    id: "visibility",
    label: VISIBILITY_META.label,
    description:
      "提及您品牌的 AI 回复总数百分比。\n数值越高表示在AI 平台中的曝光度和竞争可见度越高。",
    rankValueHeader: "可见度",
    loadingAriaLabel: "加载可见度数据",
    chartType: "line",
    formatValue: formatRate,
    formatDelta,
    yAxisMode: "rate",
  },
  {
    id: "mention",
    label: "AI 提及",
    description:
      "AI 回复正文中品牌提及的频率。反映品牌在行业主题中的存在感和受欢迎程度。数值越高表示 AI 主动讨论您品牌的倾向越强。",
    rankValueHeader: "AI 提及",
    loadingAriaLabel: "加载 AI 提及数据",
    chartType: "line",
    formatValue: formatRate,
    formatDelta,
    yAxisMode: "rate",
  },
  {
    id: "shareVoice",
    label: "声量份额",
    description:
      "品牌在 AI 内容中的提及份额比例，数值越高，获得的有效关注越多。\n反映了在激烈的市场博弈中，AI 选择讨论您而非竞品的概率。",
    rankValueHeader: "声量份额",
    loadingAriaLabel: "加载声量份额数据",
    chartType: "donut",
    formatValue: formatRate,
    formatDelta,
    yAxisMode: "rate",
  },
  {
    id: "averageRank",
    label: "平均排名",
    description:
      "品牌在AI 生成回答正文中的平均提及排名。反映了品牌在内容叙述中的优先级；排名越靠前（数值越小），越容易被用户在阅读过程中第一时间发现。",
    rankValueHeader: "平均排名",
    loadingAriaLabel: "加载平均排名数据",
    chartType: "bar",
    formatValue: formatRankMetric,
    formatDelta: formatScoreDelta,
    yAxisMode: "score",
  },
];

const EMPTY_METRIC: VisibilityMetricBundle = { rankRows: [] };

type MetricSource = {
  series?: VisibilitySeriesPoint[];
  previousSeries?: VisibilitySeriesPoint[];
  rankSeries?: SingleSeriesPoint[];
  pieLabels?: string[];
  currentShare: Record<string, number | null | undefined>;
  previousShare: Record<string, number | null | undefined>;
};

const VISIBILITY_METRIC_SOURCES: Record<
  VisibilityMetricId,
  (data: VisibilityAnalysisData) => MetricSource
> = {
  visibility: (data) => ({
    series: data.series,
    previousSeries: data.previous_series,
    currentShare: data.rank.visibility_share,
    previousShare: data.previous_rank.visibility_share,
  }),
  mention: (data) => ({
    series: data.mention_series,
    previousSeries: data.previous_mention_series,
    currentShare: data.rank.mention_share,
    previousShare: data.previous_rank.mention_share,
  }),
  shareVoice: (data) => ({
    pieLabels: data.share_voice_labels,
    currentShare: data.rank.share_voice,
    previousShare: data.previous_rank.share_voice,
  }),
  averageRank: (data) => ({
    rankSeries: data.average_rank_series,
    currentShare: data.rank.average_rank,
    previousShare: data.previous_rank.average_rank,
  }),
};

function buildPieSlices(
  labels: string[],
  share: Record<string, number | null | undefined>,
): ShareVoiceSlice[] {
  return labels.map((label) => ({
    label,
    value: share[label] ?? 0,
  }));
}

export function buildVisibilityMetricBundle(
  data: VisibilityAnalysisData | undefined,
  ownLabel: string,
  def: VisibilityMetricDefinition,
): VisibilityMetricBundle {
  if (!data) return EMPTY_METRIC;

  const source = VISIBILITY_METRIC_SOURCES[def.id](data);
  const { series, previousSeries, rankSeries, pieLabels, currentShare, previousShare } = source;
  const ownRaw = ownLabel ? currentShare[ownLabel] : undefined;
  const prevOwnRaw = ownLabel ? previousShare[ownLabel] : undefined;

  return {
    series,
    previousSeries,
    rankSeries,
    pieSlices: pieLabels ? buildPieSlices(pieLabels, currentShare) : undefined,
    ownValue: ownRaw ?? undefined,
    prevOwnValue: prevOwnRaw ?? undefined,
    rankRows:
      def.id === "averageRank"
        ? buildBrandRankRows(currentShare, previousShare, ownLabel, def.formatValue, def.formatDelta).sort(
            (a, b) => (a.valueNum ?? Infinity) - (b.valueNum ?? Infinity),
          )
        : buildBrandRankRows(currentShare, previousShare, ownLabel, def.formatValue, def.formatDelta),
  };
}

export function buildVisibilityMetricBundles(
  data: VisibilityAnalysisData | undefined,
  ownLabel: string,
): Record<VisibilityMetricId, VisibilityMetricBundle> {
  return Object.fromEntries(
    VISIBILITY_METRICS.map((def) => [def.id, buildVisibilityMetricBundle(data, ownLabel, def)]),
  ) as Record<VisibilityMetricId, VisibilityMetricBundle>;
}
