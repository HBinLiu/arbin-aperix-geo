import type { RankRow } from "@/components/analysis/common/AnalysisRankTable";
import type { ShareVoiceSlice } from "@/components/analysis/visibility/ShareVoiceDonutChart";
import {
  formatDelta,
  formatRate,
  formatRankMetric,
  formatScoreDelta,
} from "@/lib/analysis/format";
import { entityRankFlags } from "@/lib/analysis/entities";
import { ANALYSIS_DIMENSIONS } from "@/lib/analysis/nav";
import type { SingleSeriesPoint } from "@/lib/analysis/chart";
import type {
  AnalysisEntityRef,
  DashboardOverviewMetric,
  DashboardOverviewRankRow,
  VisibilityAnalysisData,
  VisibilitySeriesPoint,
} from "@/types";

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

type VisibilityMetricConfig = {
  metric: (data: VisibilityAnalysisData) => DashboardOverviewMetric;
  table: (data: VisibilityAnalysisData) => DashboardOverviewRankRow[];
  chart?: (data: VisibilityAnalysisData) => {
    cur_series: VisibilitySeriesPoint[] | SingleSeriesPoint[];
    pre_series?: VisibilitySeriesPoint[] | SingleSeriesPoint[];
  };
};

const VISIBILITY_METRIC_CONFIG: Record<VisibilityMetricId, VisibilityMetricConfig> = {
  visibility: {
    metric: (data) => data.visibility,
    table: (data) => data.visibility_table,
    chart: (data) => data.visibility_chart,
  },
  mention: {
    metric: (data) => data.mention,
    table: (data) => data.mention_table,
    chart: (data) => data.mention_chart,
  },
  shareVoice: {
    metric: (data) => data.share_voice,
    table: (data) => data.share_voice_table,
  },
  averageRank: {
    metric: (data) => data.average_rank,
    table: (data) => data.average_rank_table,
    chart: (data) => data.average_rank_chart,
  },
};

function visibilityRankRows(
  rows: DashboardOverviewRankRow[] | undefined,
  entities: AnalysisEntityRef[],
  focusEntityId: string | undefined,
  formatValue: VisibilityMetricDefinition["formatValue"],
  formatDelta: VisibilityMetricDefinition["formatDelta"],
): RankRow[] {
  return (rows ?? []).map((row) => {
    const { isOwn, isFocus } = entityRankFlags(entities, row.id, focusEntityId);
    return {
      id: row.id,
      label: row.label,
      domain: row.domain || null,
      value: formatValue(row.cur_value),
      valueNum: row.cur_value ?? undefined,
      delta: formatDelta(row.cur_value, row.pre_value),
      deltaSortNum:
        row.cur_value != null && row.pre_value != null ? row.cur_value - row.pre_value : null,
      isOwn,
      isFocus,
    };
  });
}

function shareVoicePieSlices(
  entityLabels: string[],
  table: DashboardOverviewRankRow[] | undefined,
): ShareVoiceSlice[] {
  const byId = Object.fromEntries((table ?? []).map((row) => [row.id, row]));
  return entityLabels.map((id) => {
    const row = byId[id];
    const domain = row?.domain?.trim();
    return {
      label: domain || id,
      colorKey: id,
      value: row?.cur_value ?? 0,
    };
  });
}

export function buildVisibilityMetricBundle(
  data: VisibilityAnalysisData | undefined,
  entityLabels: string[],
  entities: AnalysisEntityRef[],
  focusEntityId: string | undefined,
  def: VisibilityMetricDefinition,
): VisibilityMetricBundle {
  if (!data) return EMPTY_METRIC;

  const config = VISIBILITY_METRIC_CONFIG[def.id];
  const metric = config.metric(data);
  const rankRows = visibilityRankRows(
    config.table(data),
    entities,
    focusEntityId,
    def.formatValue,
    def.formatDelta,
  );

  if (def.id === "shareVoice") {
    return {
      pieSlices: shareVoicePieSlices(entityLabels, config.table(data)),
      ownValue: metric.current ?? undefined,
      prevOwnValue: metric.previous ?? undefined,
      rankRows,
    };
  }

  if (def.id === "averageRank") {
    const chart = config.chart?.(data);
    return {
      rankSeries: (chart?.cur_series ?? []) as SingleSeriesPoint[],
      ownValue: metric.current ?? undefined,
      prevOwnValue: metric.previous ?? undefined,
      rankRows,
    };
  }

  const chart = config.chart?.(data);
  return {
    series: (chart?.cur_series ?? []) as VisibilitySeriesPoint[],
    previousSeries: (chart?.pre_series ?? []) as VisibilitySeriesPoint[],
    ownValue: metric.current ?? undefined,
    prevOwnValue: metric.previous ?? undefined,
    rankRows,
  };
}

export function buildVisibilityMetricBundles(
  data: VisibilityAnalysisData | undefined,
  entityLabels: string[],
  entities: AnalysisEntityRef[],
  focusEntityId: string | undefined,
): Record<VisibilityMetricId, VisibilityMetricBundle> {
  return Object.fromEntries(
    VISIBILITY_METRICS.map((def) => [
      def.id,
      buildVisibilityMetricBundle(data, entityLabels, entities, focusEntityId, def),
    ]),
  ) as Record<VisibilityMetricId, VisibilityMetricBundle>;
}
