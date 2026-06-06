/** 图表入参：领域序列最小结构 */
export type MultiSeriesPoint = {
  date: string;
  values: Record<string, number>;
};

export type SingleSeriesPoint = {
  date: string;
  value: number | null;
};

export type ChartRow = {
  date: string;
  dateLabel: string;
  [key: string]: string | number;
};

export type LineConfig = {
  key: string;
  color: string;
  dashed?: boolean;
};

export type ChartLegendItem = {
  key: string;
  label: string;
  color: string;
  visible: boolean;
  interactive: boolean;
  onToggle?: () => void;
};

export type ChartTooltipRow = {
  label: string;
  value: string;
  color: string;
};

export const CHART_COLORS = [
  "#ec4899",
  "#3b82f6",
  "#14b8a6",
  "#f97316",
  "#8b5cf6",
  "#64748b",
] as const;

export const CHART_HEIGHT = 220;
export const CHART_Y_LABEL_CHAR_WIDTH = 8;
export const PREVIOUS_PERIOD_SUFFIX = " (上一期)";
export const SINGLE_SERIES_KEY = "当前";

export function formatChartDayLabel(iso: string): string {
  const d = new Date(iso);
  return `${d.getMonth() + 1}月${d.getDate()}日`;
}

export function formatChartTooltipDate(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`;
}

export function colorOfChartLabel(labels: string[], lab: string): string {
  const idx = labels.indexOf(lab);
  return CHART_COLORS[(idx >= 0 ? idx : 0) % CHART_COLORS.length];
}

export function previousPeriodDataKey(lab: string): string {
  return `${lab}${PREVIOUS_PERIOD_SUFFIX}`;
}

export function getActiveChartLabels(labels: string[], hiddenLegendKeys?: Set<string>): string[] {
  return labels.filter((l) => !hiddenLegendKeys?.has(l));
}

export function shouldOverlayPreviousPeriod({
  overlayPrevious,
  previousSeries,
  showPreviousSeries,
}: {
  overlayPrevious: boolean;
  previousSeries?: MultiSeriesPoint[];
  showPreviousSeries?: boolean;
}): boolean {
  return overlayPrevious && Boolean(previousSeries?.length) && showPreviousSeries !== false;
}

type ChartSeriesOptions = {
  multiSeries?: MultiSeriesPoint[];
  singleSeries?: SingleSeriesPoint[];
  previousSeries?: MultiSeriesPoint[];
  labels: string[];
  hiddenLegendKeys?: Set<string>;
  drawPrevious: boolean;
  showCurrentSeries?: boolean;
  showPreviousSeries?: boolean;
};

export type ChartInput = {
  multiSeries?: MultiSeriesPoint[];
  singleSeries?: SingleSeriesPoint[];
  previousSeries?: MultiSeriesPoint[];
  labels: string[];
  hiddenLegendKeys?: Set<string>;
  overlayPrevious: boolean;
  showCurrentSeries?: boolean;
  showPreviousSeries?: boolean;
  onToggleLegendKey?: (key: string) => void;
  valueFormatter: (v: number) => string;
  /** rate：0–1 比率（可见度）；score：绝对值（AI 提及） */
  yAxisMode?: "rate" | "score";
};

export type ChartModel = {
  rows: ChartRow[];
  lines: LineConfig[];
  legendItems: ChartLegendItem[];
  yMax: number;
  yTicks: number[];
  yAxisWidth: number;
  drawPrevious: boolean;
};

export function buildChartLegendItems(
  labels: string[],
  {
    hiddenLegendKeys,
    showCurrentSeries,
    showPreviousSeries,
    onToggleLegendKey,
  }: {
    hiddenLegendKeys?: Set<string>;
    showCurrentSeries: boolean;
    showPreviousSeries: boolean;
    onToggleLegendKey?: (key: string) => void;
  },
): ChartLegendItem[] {
  const interactive = Boolean(onToggleLegendKey);

  if (labels.length === 1) {
    const lab = labels[0];
    const color = CHART_COLORS[0];
    const items: ChartLegendItem[] = [];
    const currentKey = lab;
    const previousKey = previousPeriodDataKey(lab);

    if (showCurrentSeries) {
      items.push({
        key: currentKey,
        label: lab,
        color,
        visible: !hiddenLegendKeys?.has(currentKey),
        interactive,
        onToggle: onToggleLegendKey ? () => onToggleLegendKey(currentKey) : undefined,
      });
    }
    if (showPreviousSeries) {
      items.push({
        key: previousKey,
        label: previousKey,
        color,
        visible: !hiddenLegendKeys?.has(previousKey),
        interactive,
        onToggle: onToggleLegendKey ? () => onToggleLegendKey(previousKey) : undefined,
      });
    }
    return items;
  }

  return labels.map((lab, idx) => ({
    key: lab,
    label: lab,
    color: CHART_COLORS[idx % CHART_COLORS.length],
    visible: !hiddenLegendKeys?.has(lab),
    interactive,
    onToggle: onToggleLegendKey ? () => onToggleLegendKey(lab) : undefined,
  }));
}

/** 百分比比率 Y 轴友好步长（%），保证 5 档刻度均为 *.0% */
const Y_AXIS_NICE_STEPS_PCT = [1, 2, 5, 10, 15, 20, 25, 30, 40, 50];

/** 根据数据最大值生成 Y 轴上限与 5 档刻度（0、step、2×step … 4×step） */
export function buildChartYAxis(dataMax: number): { yMax: number; yTicks: number[] } {
  const paddedPct = Math.max(dataMax * 100 * 1.15, 5);
  const stepPct = Y_AXIS_NICE_STEPS_PCT.find((s) => s * 4 >= paddedPct) ?? 50;
  const step = stepPct / 100;
  const yMax = (stepPct * 4) / 100;
  const yTicks = [0, 1, 2, 3, 4].map((i) => i * step);
  return { yMax, yTicks };
}

const Y_AXIS_NICE_STEPS_SCORE = [0.25, 0.5, 1, 1.5, 2, 2.5, 5, 10];

/** AI 提及等绝对值 Y 轴（非百分比） */
export function buildChartYAxisForScore(dataMax: number): { yMax: number; yTicks: number[] } {
  const padded = Math.max(dataMax * 1.15, 0.5);
  const step = Y_AXIS_NICE_STEPS_SCORE.find((s) => s * 4 >= padded) ?? 10;
  const yMax = step * 4;
  const yTicks = [0, 1, 2, 3, 4].map((i) => i * step);
  return { yMax, yTicks };
}

export function computeChartDataMax(
  multiSeries: MultiSeriesPoint[] | undefined,
  singleSeries: SingleSeriesPoint[] | undefined,
  previousSeries: MultiSeriesPoint[] | undefined,
  activeLabels: string[],
  drawPrevious: boolean,
): number {
  let maxVal = 0.01;

  if (multiSeries) {
    for (const pt of multiSeries) {
      for (const lab of activeLabels) {
        maxVal = Math.max(maxVal, pt.values[lab] ?? 0);
      }
    }
    if (drawPrevious && previousSeries) {
      for (const pt of previousSeries) {
        for (const lab of activeLabels) {
          maxVal = Math.max(maxVal, pt.values[lab] ?? 0);
        }
      }
    }
  } else if (singleSeries) {
    for (const pt of singleSeries) {
      if (pt.value != null) maxVal = Math.max(maxVal, pt.value);
    }
  }

  return maxVal;
}

export function computeChartYAxisWidth(
  yTicks: number[],
  valueFormatter: (v: number) => string,
): number {
  const tickLabels = yTicks.map((v) => valueFormatter(v));
  const longest = Math.max(...tickLabels.map((l) => l.length), 0);
  return Math.max(36, longest * CHART_Y_LABEL_CHAR_WIDTH + 8);
}

/** 领域序列 → Recharts 扁平行数据 */
export function toChartRows({
  multiSeries,
  singleSeries,
  previousSeries,
  labels,
  hiddenLegendKeys,
  drawPrevious,
  showCurrentSeries,
  showPreviousSeries,
}: ChartSeriesOptions): ChartRow[] {
  const dates =
    multiSeries?.map((p) => p.date) ?? singleSeries?.map((p) => p.date) ?? [];
  const activeLabels = getActiveChartLabels(labels, hiddenLegendKeys);

  return dates.map((date, i) => {
    const row: ChartRow = { date, dateLabel: formatChartDayLabel(date) };

    if (multiSeries && activeLabels.length > 0) {
      activeLabels.forEach((lab) => {
        if (showCurrentSeries !== false) {
          row[lab] = multiSeries[i]?.values[lab] ?? 0;
        }
        if (drawPrevious && showPreviousSeries !== false) {
          const prevKey = previousPeriodDataKey(lab);
          if (!hiddenLegendKeys?.has(prevKey)) {
            row[prevKey] = previousSeries?.[i]?.values[lab] ?? 0;
          }
        }
      });
    } else if (singleSeries && showCurrentSeries !== false) {
      row[SINGLE_SERIES_KEY] = singleSeries[i]?.value ?? 0;
    }

    return row;
  });
}

export function toLineConfigs({
  multiSeries,
  singleSeries,
  labels,
  hiddenLegendKeys,
  drawPrevious,
  showCurrentSeries,
  showPreviousSeries,
}: ChartSeriesOptions): LineConfig[] {
  const activeLabels = getActiveChartLabels(labels, hiddenLegendKeys);
  const lines: LineConfig[] = [];

  if (multiSeries && activeLabels.length > 0) {
    activeLabels.forEach((lab, idx) => {
      const color = CHART_COLORS[idx % CHART_COLORS.length];
      if (showCurrentSeries !== false) {
        lines.push({ key: lab, color });
      }
      if (drawPrevious && showPreviousSeries !== false) {
        const prevKey = previousPeriodDataKey(lab);
        if (!hiddenLegendKeys?.has(prevKey)) {
          lines.push({ key: prevKey, color, dashed: true });
        }
      }
    });
    return lines;
  }

  if (singleSeries && showCurrentSeries !== false) {
    lines.push({ key: SINGLE_SERIES_KEY, color: CHART_COLORS[0] });
  }

  return lines;
}

/** 领域序列 → Recharts 渲染模型 */
export function buildChartModel(input: ChartInput): ChartModel {
  const {
    multiSeries,
    singleSeries,
    previousSeries,
    labels,
    hiddenLegendKeys,
    overlayPrevious,
    showCurrentSeries = true,
    showPreviousSeries = true,
    onToggleLegendKey,
    valueFormatter,
    yAxisMode = "rate",
  } = input;

  const drawPrevious = shouldOverlayPreviousPeriod({
    overlayPrevious,
    previousSeries,
    showPreviousSeries,
  });

  const seriesOptions: ChartSeriesOptions = {
    multiSeries,
    singleSeries,
    previousSeries,
    labels,
    hiddenLegendKeys,
    drawPrevious,
    showCurrentSeries,
    showPreviousSeries,
  };

  const activeLabels = getActiveChartLabels(labels, hiddenLegendKeys);
  const rows = toChartRows(seriesOptions);
  const lines = toLineConfigs(seriesOptions);
  const legendItems = buildChartLegendItems(labels, {
    hiddenLegendKeys,
    showCurrentSeries,
    showPreviousSeries: drawPrevious && showPreviousSeries !== false,
    onToggleLegendKey,
  });

  const dataMax = computeChartDataMax(
    multiSeries,
    singleSeries,
    previousSeries,
    activeLabels,
    drawPrevious,
  );
  const { yMax, yTicks } =
    yAxisMode === "score" ? buildChartYAxisForScore(dataMax) : buildChartYAxis(dataMax);
  const yAxisWidth = computeChartYAxisWidth(yTicks, valueFormatter);

  return { rows, lines, legendItems, yMax, yTicks, yAxisWidth, drawPrevious };
}

/** 悬停点各序列原始值 → tooltip 行（与具体图表库无关） */
export function buildChartTooltipRows({
  valuesByKey,
  labels,
  hiddenLegendKeys,
  overlayPrevious,
  previousSeries,
  showCurrentSeries,
  showPreviousSeries,
  valueFormatter,
}: {
  valuesByKey: Record<string, number>;
  labels: string[];
  hiddenLegendKeys?: Set<string>;
  overlayPrevious: boolean;
  previousSeries?: MultiSeriesPoint[];
  showCurrentSeries?: boolean;
  showPreviousSeries?: boolean;
  valueFormatter: (v: number) => string;
}): ChartTooltipRow[] {
  const activeLabels = getActiveChartLabels(labels, hiddenLegendKeys);
  const isPreviousPeriodMode =
    overlayPrevious && Boolean(previousSeries?.length) && activeLabels.length > 0;

  if (isPreviousPeriodMode) {
    const rows: ChartTooltipRow[] = [];
    if (showCurrentSeries !== false) {
      activeLabels.forEach((lab) => {
        rows.push({
          label: lab,
          value: valueFormatter(valuesByKey[lab] ?? 0),
          color: colorOfChartLabel(labels, lab),
        });
      });
    }
    if (showPreviousSeries !== false) {
      activeLabels.forEach((lab) => {
        const key = previousPeriodDataKey(lab);
        rows.push({
          label: key,
          value: valueFormatter(valuesByKey[key] ?? 0),
          color: colorOfChartLabel(labels, lab),
        });
      });
    }
    return rows;
  }

  if (showCurrentSeries === false) return [];

  return activeLabels
    .map((lab) => ({
      label: lab,
      value: valueFormatter(valuesByKey[lab] ?? 0),
      color: colorOfChartLabel(labels, lab),
      sortValue: valuesByKey[lab] ?? 0,
    }))
    .sort((a, b) => b.sortValue - a.sortValue)
    .map(({ label, value, color }) => ({ label, value, color }));
}
