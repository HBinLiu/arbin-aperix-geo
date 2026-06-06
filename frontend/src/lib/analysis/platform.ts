import type { RankRow } from "@/components/analysis/common/AnalysisRankTable";
import {
  formatDelta,
  formatRankMetric,
  formatRate,
  formatScoreDelta,
  formatSentimentDelta,
  formatSentimentScore,
} from "@/lib/analysis/format";
import { resolvePlatformMeta } from "@/lib/analysis/shared";
import type {
  PlatformMatrixData,
  PlatformMatrixMetricId,
  PlatformMatrixRowDimension,
  PlatformMatrixSeriesPoint,
  PlatformPerformance,
  SamplingPlatform,
} from "@/types";

export const PLATFORM_PAGE_TITLE = "平台可见度矩阵";
export const PLATFORM_PAGE_DESCRIPTION =
  "全景式评估品牌在主流 AI 平台上的竞争站位，提示平台间的流量分布差异与特定算法的推荐偏好，定向调整优化策略以填补生态覆盖缺口。";

export const PLATFORM_MATRIX_ROW_OPTIONS: { id: PlatformMatrixRowDimension; label: string }[] = [
  { id: "competitor", label: "竞争对手" },
  { id: "topic", label: "品牌主题" },
];

export type PlatformMatrixMetricDefinition = {
  id: PlatformMatrixMetricId;
  label: string;
  rankHeader: string;
  yAxisMode: "rate" | "score";
  formatValue: (value: number | null | undefined) => string;
  formatDelta: (
    current: number | null | undefined,
    previous: number | null | undefined,
  ) => string | null;
  pickPerformance: (row: PlatformPerformance) => number | null | undefined;
  seriesKey: keyof PlatformMatrixData["platform_series"][string];
};

export const PLATFORM_MATRIX_METRICS: PlatformMatrixMetricDefinition[] = [
  {
    id: "visibility",
    label: "可见度",
    rankHeader: "可见度",
    yAxisMode: "rate",
    formatValue: formatRate,
    formatDelta: formatDelta,
    pickPerformance: (row) => row.visibility_rate,
    seriesKey: "visibility",
  },
  {
    id: "citation",
    label: "引用率",
    rankHeader: "引用率",
    yAxisMode: "rate",
    formatValue: formatRate,
    formatDelta: formatDelta,
    pickPerformance: (row) => row.citation_rate,
    seriesKey: "citation",
  },
  {
    id: "shareVoice",
    label: "声量份额",
    rankHeader: "声量份额",
    yAxisMode: "rate",
    formatValue: formatRate,
    formatDelta: formatDelta,
    pickPerformance: (row) => row.share_voice,
    seriesKey: "share_voice",
  },
  {
    id: "averageRank",
    label: "平均排名",
    rankHeader: "平均排名",
    yAxisMode: "score",
    formatValue: formatRankMetric,
    formatDelta: formatScoreDelta,
    pickPerformance: (row) => row.average_rank,
    seriesKey: "average_rank",
  },
  {
    id: "sentiment",
    label: "情感倾向",
    rankHeader: "情感倾向",
    yAxisMode: "score",
    formatValue: formatSentimentScore,
    formatDelta: formatSentimentDelta,
    pickPerformance: (row) => row.sentiment_score,
    seriesKey: "sentiment",
  },
];

const METRIC_VALUE_KEY: Record<
  PlatformMatrixMetricId,
  keyof PlatformMatrixData["competitor_values"]
> = {
  visibility: "visibility",
  shareVoice: "share_voice",
  citation: "citation",
  averageRank: "average_rank",
  sentiment: "sentiment",
};

export function platformMatrixMetric(id: PlatformMatrixMetricId): PlatformMatrixMetricDefinition {
  return PLATFORM_MATRIX_METRICS.find((metric) => metric.id === id) ?? PLATFORM_MATRIX_METRICS[0];
}

export function buildPlatformRankRows(
  current: PlatformPerformance[],
  platformsMeta: SamplingPlatform[],
  definition: PlatformMatrixMetricDefinition,
): RankRow[] {
  return [...current]
    .sort((a, b) => (definition.pickPerformance(b) ?? -1) - (definition.pickPerformance(a) ?? -1))
    .map((row) => {
      const meta = resolvePlatformMeta(row.platform, platformsMeta);
      const valueNum = definition.pickPerformance(row);
      return {
        id: row.platform,
        label: meta.label,
        value: definition.formatValue(valueNum),
        valueNum: valueNum ?? undefined,
        delta: null,
      };
    });
}

export type PlatformMatrixRow = {
  id: string;
  label: string;
  isOwn?: boolean;
  values: Record<string, number | null | undefined>;
};

export function buildPlatformMatrixRows(
  data: PlatformMatrixData,
  rowDimension: PlatformMatrixRowDimension,
  metricId: PlatformMatrixMetricId,
): PlatformMatrixRow[] {
  const metricKey = METRIC_VALUE_KEY[metricId];
  const valueMap =
    rowDimension === "competitor" ? data.competitor_values[metricKey] : data.topic_values[metricKey];
  const rows =
    rowDimension === "competitor"
      ? data.competitor_rows.map((row) => ({
          id: row.id,
          label: row.label,
          isOwn: row.is_own,
          values: valueMap[row.label] ?? {},
        }))
      : data.topic_rows.map((row) => ({
          id: row.id,
          label: row.label,
          values: valueMap[row.id] ?? {},
        }));

  return rows;
}

export function selectedPlatformSeries(
  data: PlatformMatrixData | undefined,
  platformId: string | null,
  metric: PlatformMatrixMetricDefinition,
): PlatformMatrixSeriesPoint[] {
  if (!data || !platformId) return [];
  return data.platform_series[platformId]?.[metric.seriesKey] ?? [];
}

export function selectedPlatformMetricValue(
  data: PlatformMatrixData | undefined,
  platformId: string | null,
  metric: PlatformMatrixMetricDefinition,
): number | null | undefined {
  if (!data || !platformId) return null;
  const row = data.platform_performance.find((item) => item.platform === platformId);
  return row ? metric.pickPerformance(row) : null;
}

export type PlatformMetricBundle = {
  value: number | null | undefined;
  series: PlatformMatrixSeriesPoint[];
  rankRows: RankRow[];
};

/** 平台页各指标的趋势、当前值与排名（一次 API 数据构建全部指标） */
export function buildPlatformMetricBundles(
  data: PlatformMatrixData | undefined,
  selectedPlatformId: string | null,
  platformsMeta: SamplingPlatform[],
): Record<PlatformMatrixMetricId, PlatformMetricBundle> {
  const bundles = {} as Record<PlatformMatrixMetricId, PlatformMetricBundle>;
  for (const definition of PLATFORM_MATRIX_METRICS) {
    bundles[definition.id] = {
      value: selectedPlatformMetricValue(data, selectedPlatformId, definition),
      series: selectedPlatformSeries(data, selectedPlatformId, definition),
      rankRows: data
        ? buildPlatformRankRows(data.platform_performance, platformsMeta, definition)
        : [],
    };
  }
  return bundles;
}

/** 平台页指标区块布局：每个指标独占一行 */
export const PLATFORM_METRIC_LAYOUT: PlatformMatrixMetricId[][] = [
  ["visibility"],
  ["citation"],
  ["shareVoice"],
  ["averageRank"],
  ["sentiment"],
];
