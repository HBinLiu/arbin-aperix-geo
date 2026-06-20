import type { RankRow } from "@/components/analysis/common/AnalysisRankTable";
import type { MultiSeriesPoint } from "@/lib/analysis/chart";
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
  AnalysisEntityRef,
  PlatformAnalysisData,
  PlatformMatrixCell,
  PlatformMatrixCells,
  PlatformMatrixMetricId,
  PlatformMatrixRowDimension,
  PlatformChartWindow,
  PlatformPerformance,
  PlatformSeriesMetric,
  SamplingPlatform,
  SubjectTopic,
} from "@/types";

/** 兼容旧版 API 返回的扁平 cell 数组 */
export function normalizePlatformMatrixCells(
  cells: PlatformMatrixCells | PlatformMatrixCell[] | null | undefined,
): PlatformMatrixCells {
  if (cells == null) return { current: [], previous: [] };
  if (Array.isArray(cells)) return { current: cells, previous: [] };
  return {
    current: cells.current ?? [],
    previous: cells.previous ?? [],
  };
}

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
  description: string;
  rankHeader: string;
  yAxisMode: "rate" | "score";
  formatValue: (value: number | null | undefined) => string;
  formatDelta: (
    current: number | null | undefined,
    previous: number | null | undefined,
  ) => string | null;
  pickPerformance: (row: PlatformPerformance) => number | null | undefined;
  seriesMetric: PlatformSeriesMetric;
};

export function platformMatrixMetricDescription(label: string): string {
  return `当前品牌在每个 AI 平台的${label}趋势`;
}

export const PLATFORM_MATRIX_METRICS: PlatformMatrixMetricDefinition[] = [
  {
    id: "visibility",
    label: "可见度",
    description: platformMatrixMetricDescription("可见度"),
    rankHeader: "可见度",
    yAxisMode: "rate",
    formatValue: formatRate,
    formatDelta: formatDelta,
    pickPerformance: (row) => row.visibility_rate,
    seriesMetric: "visibility",
  },
  {
    id: "citation",
    label: "引用率",
    description: platformMatrixMetricDescription("引用率"),
    rankHeader: "引用率",
    yAxisMode: "rate",
    formatValue: formatRate,
    formatDelta: formatDelta,
    pickPerformance: (row) => row.citation_rate,
    seriesMetric: "citation",
  },
  {
    id: "shareVoice",
    label: "声量份额",
    description: platformMatrixMetricDescription("声量份额"),
    rankHeader: "声量份额",
    yAxisMode: "rate",
    formatValue: formatRate,
    formatDelta: formatDelta,
    pickPerformance: (row) => row.share_voice,
    seriesMetric: "share_voice",
  },
  {
    id: "averageRank",
    label: "平均排名",
    description: platformMatrixMetricDescription("平均排名"),
    rankHeader: "平均排名",
    yAxisMode: "score",
    formatValue: formatRankMetric,
    formatDelta: formatScoreDelta,
    pickPerformance: (row) => row.average_rank,
    seriesMetric: "average_rank",
  },
  {
    id: "sentiment",
    label: "情感倾向",
    description: platformMatrixMetricDescription("情感倾向"),
    rankHeader: "情感倾向",
    yAxisMode: "score",
    formatValue: formatSentimentScore,
    formatDelta: formatSentimentDelta,
    pickPerformance: (row) => row.sentiment_score,
    seriesMetric: "sentiment",
  },
];

type PlatformMatrixMetricField =
  | "visibility_rate"
  | "share_voice"
  | "citation_rate"
  | "average_rank"
  | "sentiment_score";

const METRIC_CELL_FIELD: Record<PlatformMatrixMetricId, PlatformMatrixMetricField> = {
  visibility: "visibility_rate",
  shareVoice: "share_voice",
  citation: "citation_rate",
  averageRank: "average_rank",
  sentiment: "sentiment_score",
};

export function platformMatrixMetric(id: PlatformMatrixMetricId): PlatformMatrixMetricDefinition {
  return PLATFORM_MATRIX_METRICS.find((metric) => metric.id === id) ?? PLATFORM_MATRIX_METRICS[0];
}

export function buildPlatformRankRows(
  current: PlatformPerformance[],
  previous: PlatformPerformance[],
  platformIds: string[],
  platformsMeta: SamplingPlatform[],
  definition: PlatformMatrixMetricDefinition,
): RankRow[] {
  const currentByPlatform = Object.fromEntries(current.map((row) => [row.platform, row]));
  const prevByPlatform = Object.fromEntries(previous.map((row) => [row.platform, row]));

  return platformIds
    .map((platformId) => {
      const meta = resolvePlatformMeta(platformId, platformsMeta);
      const row = currentByPlatform[platformId];
      const prevRow = prevByPlatform[platformId];
      const valueNum = row ? definition.pickPerformance(row) : undefined;
      const prevValueNum = prevRow ? definition.pickPerformance(prevRow) : undefined;
      return {
        id: platformId,
        label: meta.label,
        value: definition.formatValue(valueNum),
        valueNum: valueNum ?? undefined,
        delta: definition.formatDelta(valueNum, prevValueNum),
        deltaSortNum:
          valueNum != null && prevValueNum != null ? valueNum - prevValueNum : null,
      };
    })
    .sort((a, b) => (b.valueNum ?? -1) - (a.valueNum ?? -1));
}

export type PlatformMatrixRow = {
  id: string;
  label: string;
  /** 竞争对手 favicon 域名键（entity.label） */
  domain?: string;
  isOwn?: boolean;
  /** FilterBar 当前分析对象（竞品视角） */
  isFocus?: boolean;
  values: Record<string, number | null | undefined>;
  previousValues: Record<string, number | null | undefined>;
};

function matrixCells(
  data: PlatformAnalysisData,
  period: "current" | "previous",
): PlatformMatrixCell[] {
  return normalizePlatformMatrixCells(data.matrix_cells)[period];
}

function valuesByRow(
  cells: PlatformMatrixCell[],
  rowId: string,
  field: PlatformMatrixMetricField,
): Record<string, number | null | undefined> {
  return Object.fromEntries(
    cells.filter((cell) => cell.row_id === rowId).map((cell) => [cell.platform_id, cell[field]]),
  );
}

export function buildPlatformMatrixRows(
  data: PlatformAnalysisData,
  rowDimension: PlatformMatrixRowDimension,
  metricId: PlatformMatrixMetricId,
  entities: AnalysisEntityRef[] = [],
  topics: SubjectTopic[] = [],
): PlatformMatrixRow[] {
  const field = METRIC_CELL_FIELD[metricId];
  const currentCells = matrixCells(data, "current");
  const previousCells = matrixCells(data, "previous");
  const rows =
    rowDimension === "competitor"
      ? entities.map((entity) => ({
          id: entity.id,
          label: entity.display_name,
          domain: entity.label,
          isOwn: entity.kind === "own",
          isFocus: entity.id === data.entity_id,
        }))
      : [...topics]
          .sort((a, b) => a.name.localeCompare(b.name))
          .map((topic) => ({
            id: topic.id,
            label: topic.name,
          }));

  return rows.map((row) => ({
    ...row,
    values: valuesByRow(currentCells, row.id, field),
    previousValues: valuesByRow(previousCells, row.id, field),
  }));
}

export function buildPlatformChartSeries(
  chart: PlatformChartWindow | undefined,
  platformIds: string[],
  platformsMeta: SamplingPlatform[],
): { multiSeries: MultiSeriesPoint[]; chartLabels: string[] } {
  if (!chart || platformIds.length === 0) {
    return { multiSeries: [], chartLabels: [] };
  }

  const chartLabels = platformIds.map((id) => resolvePlatformMeta(id, platformsMeta).label);
  const labelByPlatformId = Object.fromEntries(platformIds.map((id, index) => [id, chartLabels[index]]));

  const multiSeries: MultiSeriesPoint[] = chart.current.map((point) => ({
    date: point.date,
    values: Object.fromEntries(
      platformIds
        .filter((id) => point.values[id] != null)
        .map((id) => [labelByPlatformId[id], point.values[id]]),
    ),
  }));

  return { multiSeries, chartLabels };
}

export type PlatformMetricBundle = {
  multiSeries: MultiSeriesPoint[];
  chartLabels: string[];
  rankRows: RankRow[];
};

/** 平台页各指标的趋势与排名（一次 API 数据构建全部指标） */
export function buildPlatformMetricBundles(
  data: PlatformAnalysisData | undefined,
  platformIds: string[],
  platformsMeta: SamplingPlatform[],
): Record<PlatformMatrixMetricId, PlatformMetricBundle> {
  const bundles = {} as Record<PlatformMatrixMetricId, PlatformMetricBundle>;
  for (const definition of PLATFORM_MATRIX_METRICS) {
    const { multiSeries, chartLabels } = buildPlatformChartSeries(
      data?.charts?.[definition.seriesMetric],
      platformIds,
      platformsMeta,
    );
    bundles[definition.id] = {
      multiSeries,
      chartLabels,
      rankRows: data
        ? buildPlatformRankRows(
            data.performance.current,
            data.performance.previous,
            platformIds,
            platformsMeta,
            definition,
          )
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
