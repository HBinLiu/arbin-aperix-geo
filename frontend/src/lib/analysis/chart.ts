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

/** 黄金角步进：相邻序号色相区分度大 */
const CHART_GOLDEN_ANGLE = 137.508;
/** 与产品主色（粉）对齐的起始色相 */
const CHART_HUE_OFFSET = 330;
/** 交替饱和度 / 明度，进一步拉开相近色相的视觉差异 */
const CHART_SATURATIONS = [70, 58, 76, 52] as const;
const CHART_LIGHTNESSES = [48, 40, 54, 44] as const;

function hashString(input: string): number {
  let hash = 0;
  for (let i = 0; i < input.length; i++) {
    hash = (hash * 31 + input.charCodeAt(i)) >>> 0;
  }
  return hash;
}

function hslToHex(hue: number, saturation: number, lightness: number): string {
  const h = hue / 360;
  const s = saturation / 100;
  const l = lightness / 100;
  const hue2rgb = (p: number, q: number, t: number) => {
    let tt = t;
    if (tt < 0) tt += 1;
    if (tt > 1) tt -= 1;
    if (tt < 1 / 6) return p + (q - p) * 6 * tt;
    if (tt < 1 / 2) return q;
    if (tt < 2 / 3) return p + (q - p) * (2 / 3 - tt) * 6;
    return p;
  };
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  const r = Math.round(hue2rgb(p, q, h + 1 / 3) * 255);
  const g = Math.round(hue2rgb(p, q, h) * 255);
  const b = Math.round(hue2rgb(p, q, h - 1 / 3) * 255);
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
}

function hslColor(hue: number, saturation: number, lightness: number): string {
  return hslToHex(hue, saturation, lightness);
}

/** 按列表序号取色：黄金角色相 + 饱和度/明度交错 */
export function chartColorAtIndex(index: number): string {
  const hue = (CHART_HUE_OFFSET + index * CHART_GOLDEN_ANGLE) % 360;
  const saturation = CHART_SATURATIONS[index % CHART_SATURATIONS.length];
  const lightness = CHART_LIGHTNESSES[Math.floor(index / 2) % CHART_LIGHTNESSES.length];
  return hslColor(hue, saturation, lightness);
}

/**
 * 为当前图表内的监测项分配颜色：按名称稳定排序后用序号取色，
 * 同屏 N 项时色相约 360/N 间隔，比纯哈希更少撞色。
 */
export function buildChartColorLookup(labels: readonly string[]): ReadonlyMap<string, string> {
  const unique = [...new Set(labels.map((label) => label.trim()).filter(Boolean))];
  unique.sort((a, b) => a.localeCompare(b, "zh-CN"));
  const map = new Map<string, string>();
  unique.forEach((label, index) => {
    map.set(label, chartColorAtIndex(index));
  });
  return map;
}

/** 按名称取稳定色（无同屏列表时的回退，仍走黄金角序号） */
export function chartColorForKey(key: string): string {
  const normalized = key.trim() || "?";
  return chartColorAtIndex(hashString(normalized) % 360);
}

export function chartColorFromLookup(
  lookup: ReadonlyMap<string, string>,
  label: string,
): string {
  return lookup.get(label.trim()) ?? chartColorForKey(label);
}

function resolveChartColor(
  colorLookup: ReadonlyMap<string, string> | undefined,
  labels: string[],
  key: string,
): string {
  const normalized = key.trim();
  const fromLookup = colorLookup?.get(normalized);
  if (fromLookup) return fromLookup;
  if (labels.length > 0) {
    const hit = buildChartColorLookup(labels).get(normalized);
    if (hit) return hit;
  }
  return chartColorForKey(key);
}

export const CHART_HEIGHT = 220;
export const CHART_Y_LABEL_CHAR_WIDTH = 8;
export const PREVIOUS_PERIOD_SUFFIX = " (上一期)";
export const SINGLE_SERIES_KEY = "当前";

/** series key → 展示名（legendLabels 由 entityDisplayName 构建；支持「上一期」后缀 key） */
export function chartDisplayLabel(
  seriesKey: string,
  legendLabels?: Readonly<Record<string, string>>,
  fallback?: string,
): string {
  const resolved = fallback ?? seriesKey;
  if (!legendLabels) return resolved;
  if (seriesKey.endsWith(PREVIOUS_PERIOD_SUFFIX)) {
    const baseKey = seriesKey.slice(0, -PREVIOUS_PERIOD_SUFFIX.length);
    return `${legendLabels[baseKey] ?? baseKey}${PREVIOUS_PERIOD_SUFFIX}`;
  }
  return legendLabels[seriesKey] ?? resolved;
}

/** 从扁平行读取序列值（Recharts row payload） */
export function chartRowValue(row: ChartRow, key: string): number {
  const value = row[key];
  return typeof value === "number" ? value : Number(value ?? 0);
}

/** 百分比比率 Y 轴：按数据 max 自适应上限，刻度交给 Recharts tickCount */
export function buildChartYAxis(dataMax: number): { yMin: number; yMax: number } {
  return {
    yMin: 0,
    yMax: Math.max(dataMax * 1, 0.01),
  };
}

export function computeChartDataRange(
  rows: ChartRow[],
  lineKeys: string[],
): { min: number; max: number } {
  let min = Infinity;
  let max = 0.01;

  for (const row of rows) {
    for (const key of lineKeys) {
      const value = chartRowValue(row, key);
      if (!Number.isFinite(value)) continue;
      min = Math.min(min, value);
      max = Math.max(max, value);
    }
  }

  if (!Number.isFinite(min)) min = 0;
  return { min, max };
}

/** @deprecated 使用 computeChartDataRange */
export function computeChartDataMax(rows: ChartRow[], lineKeys: string[]): number {
  return computeChartDataRange(rows, lineKeys).max;
}

export function computeChartYAxisWidth(
  yMin: number,
  yMax: number,
  valueFormatter: (v: number) => string,
): number {
  const samples = [yMin, yMin + (yMax - yMin) * 0.5, yMax];
  const tickLabels = samples.map((v) => valueFormatter(v));
  const longest = Math.max(...tickLabels.map((l) => l.length), 0);
  return Math.max(36, longest * CHART_Y_LABEL_CHAR_WIDTH + 8);
}

export function formatChartDayLabel(iso: string): string {
  const d = new Date(iso);
  return `${d.getMonth() + 1}月${d.getDate()}日`;
}

const CHART_X_AXIS_LABEL_WIDTH_FULL = 52;
const CHART_X_AXIS_LABEL_WIDTH_COMPACT = 34;

function formatChartAxisTickLabel(iso: string, compact: boolean): string {
  const d = new Date(iso);
  if (compact) {
    return `${d.getMonth() + 1}/${d.getDate()}`;
  }
  return formatChartDayLabel(iso);
}

/** 按绘图区宽度选择标签格式与 minTickGap，刻度数量交给 Recharts 自适应 */
export function resolveChartXAxisLayout(
  plotWidth: number,
  pointCount: number,
): { compactLabels: boolean; minTickGap: number; formatTick: (iso: string) => string } {
  const fitsFullLabels =
    pointCount <= 1 || plotWidth <= 0 || pointCount * CHART_X_AXIS_LABEL_WIDTH_FULL <= plotWidth;
  const compactLabels = !fitsFullLabels;
  const minTickGap = fitsFullLabels
    ? CHART_X_AXIS_LABEL_WIDTH_FULL
    : CHART_X_AXIS_LABEL_WIDTH_COMPACT;

  return {
    compactLabels,
    minTickGap,
    formatTick: (iso: string) => formatChartAxisTickLabel(iso, compactLabels),
  };
}

export function formatChartTooltipDate(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`;
}

export function colorOfChartLabel(labels: string[], lab: string): string {
  return resolveChartColor(undefined, labels, lab);
}

export function previousPeriodDataKey(lab: string): string {
  return `${lab}${PREVIOUS_PERIOD_SUFFIX}`;
}

export function getActiveChartLabels(labels: string[], hiddenLegendKeys?: Set<string>): string[] {
  return labels.filter((l) => !hiddenLegendKeys?.has(l));
}

/** labels 未传或与序列键不匹配时，从 multiSeries 的 values 键推断 */
export function inferChartLabels(
  labels: string[],
  multiSeries?: MultiSeriesPoint[],
): string[] {
  const valueKeys = new Set<string>();
  for (const point of multiSeries ?? []) {
    for (const key of Object.keys(point.values ?? {})) {
      if (key.trim()) valueKeys.add(key.trim());
    }
  }

  if (labels.length === 0) {
    return [...valueKeys].sort((a, b) => a.localeCompare(b, "zh-CN"));
  }

  if (valueKeys.size > 0 && !labels.some((label) => valueKeys.has(label.trim()))) {
    return [...valueKeys].sort((a, b) => a.localeCompare(b, "zh-CN"));
  }

  return labels;
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
  colorLookup?: ReadonlyMap<string, string>;
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
  valueFormatter?: (v: number) => string;
  /** rate：0–1 比率（可见度）；score：绝对值（AI 提及） */
  yAxisMode?: "rate" | "score";
};

export type ChartModel = {
  rows: ChartRow[];
  lines: LineConfig[];
  legendItems: ChartLegendItem[];
  colorLookup: ReadonlyMap<string, string>;
  yMin: number;
  yMax: number;
  yAxisWidth: number;
  drawPrevious: boolean;
  labels: string[];
  hiddenLegendKeys?: Set<string>;
  overlayPrevious: boolean;
  previousSeries?: MultiSeriesPoint[];
  showCurrentSeries: boolean;
  showPreviousSeries: boolean;
};

function buildChartLegendItems(
  labels: string[],
  {
    hiddenLegendKeys,
    showCurrentSeries,
    showPreviousSeries,
    onToggleLegendKey,
    colorLookup,
  }: {
    hiddenLegendKeys?: Set<string>;
    showCurrentSeries: boolean;
    showPreviousSeries: boolean;
    onToggleLegendKey?: (key: string) => void;
    colorLookup?: ReadonlyMap<string, string>;
  },
): ChartLegendItem[] {
  const interactive = Boolean(onToggleLegendKey);

  if (labels.length === 1) {
    const lab = labels[0];
    const color = resolveChartColor(colorLookup, labels, lab);
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

  return labels.map((lab) => ({
    key: lab,
    label: lab,
    color: resolveChartColor(colorLookup, labels, lab),
    visible: !hiddenLegendKeys?.has(lab),
    interactive,
    onToggle: onToggleLegendKey ? () => onToggleLegendKey(lab) : undefined,
  }));
}

/** 领域序列 → Recharts 扁平行数据 */
function toChartRows({
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
    const row: ChartRow = { date };

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

function toLineConfigs({
  multiSeries,
  singleSeries,
  labels,
  hiddenLegendKeys,
  drawPrevious,
  showCurrentSeries,
  showPreviousSeries,
  colorLookup,
}: ChartSeriesOptions): LineConfig[] {
  const activeLabels = getActiveChartLabels(labels, hiddenLegendKeys);
  const lines: LineConfig[] = [];

  if (multiSeries && activeLabels.length > 0) {
    activeLabels.forEach((lab) => {
      const color = resolveChartColor(colorLookup, labels, lab);
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
    lines.push({ key: SINGLE_SERIES_KEY, color: chartColorForKey(SINGLE_SERIES_KEY) });
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
    valueFormatter = (v) => String(v),
  } = input;

  const drawPrevious = shouldOverlayPreviousPeriod({
    overlayPrevious,
    previousSeries,
    showPreviousSeries,
  });

  const resolvedLabels = inferChartLabels(labels, multiSeries);
  const colorLookup = buildChartColorLookup(resolvedLabels);

  const seriesOptions: ChartSeriesOptions = {
    multiSeries,
    singleSeries,
    previousSeries,
    labels: resolvedLabels,
    hiddenLegendKeys,
    drawPrevious,
    showCurrentSeries,
    showPreviousSeries,
    colorLookup,
  };

  const rows = toChartRows(seriesOptions);
  const lines = toLineConfigs(seriesOptions);
  const legendItems = buildChartLegendItems(resolvedLabels, {
    hiddenLegendKeys,
    showCurrentSeries,
    showPreviousSeries: drawPrevious && showPreviousSeries !== false,
    onToggleLegendKey,
    colorLookup,
  });

  const lineKeys = lines.map((line) => line.key);
  const { max: dataMax } = computeChartDataRange(rows, lineKeys);
  const { yMin, yMax } = buildChartYAxis(dataMax);
  const yAxisWidth = computeChartYAxisWidth(yMin, yMax, valueFormatter);

  return {
    rows,
    lines,
    legendItems,
    colorLookup,
    yMin,
    yMax,
    yAxisWidth,
    drawPrevious,
    labels: resolvedLabels,
    hiddenLegendKeys,
    overlayPrevious,
    previousSeries,
    showCurrentSeries,
    showPreviousSeries,
  };
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
  colorLookup,
  fallbackLabel,
  legendLabels,
}: {
  valuesByKey: Record<string, number>;
  labels: string[];
  hiddenLegendKeys?: Set<string>;
  overlayPrevious: boolean;
  previousSeries?: MultiSeriesPoint[];
  showCurrentSeries?: boolean;
  showPreviousSeries?: boolean;
  valueFormatter: (v: number) => string;
  colorLookup?: ReadonlyMap<string, string>;
  /** 单序列模式（dataKey 为 SINGLE_SERIES_KEY）时的展示标签 */
  fallbackLabel?: string;
  /** series key → 展示名（brand 优先） */
  legendLabels?: Readonly<Record<string, string>>;
}): ChartTooltipRow[] {
  const activeLabels = getActiveChartLabels(labels, hiddenLegendKeys);
  const isPreviousPeriodMode =
    overlayPrevious && Boolean(previousSeries?.length) && activeLabels.length > 0;
  const color = (lab: string) => resolveChartColor(colorLookup, labels, lab);

  const singleSeriesValue = valuesByKey[SINGLE_SERIES_KEY];
  const singleSeriesOnly =
    singleSeriesValue != null && activeLabels.every((lab) => valuesByKey[lab] == null);
  if (singleSeriesOnly) {
    const displayLabels =
      activeLabels.length > 0 ? activeLabels : [fallbackLabel ?? SINGLE_SERIES_KEY];
    return displayLabels.map((lab) => ({
      label: chartDisplayLabel(lab, legendLabels),
      value: valueFormatter(singleSeriesValue),
      color: color(lab),
    }));
  }

  if (isPreviousPeriodMode) {
    const rows: ChartTooltipRow[] = [];
    if (showCurrentSeries !== false) {
      activeLabels.forEach((lab) => {
        rows.push({
          label: chartDisplayLabel(lab, legendLabels),
          value: valueFormatter(valuesByKey[lab] ?? 0),
          color: color(lab),
        });
      });
    }
    if (showPreviousSeries !== false) {
      activeLabels.forEach((lab) => {
        const key = previousPeriodDataKey(lab);
        rows.push({
          label: chartDisplayLabel(key, legendLabels),
          value: valueFormatter(valuesByKey[key] ?? 0),
          color: color(lab),
        });
      });
    }
    return rows;
  }

  if (showCurrentSeries === false) return [];

  return activeLabels
    .map((lab) => ({
      label: chartDisplayLabel(lab, legendLabels),
      value: valueFormatter(valuesByKey[lab] ?? 0),
      color: color(lab),
      sortValue: valuesByKey[lab] ?? 0,
    }))
    .sort((a, b) => b.sortValue - a.sortValue)
    .map(({ label, value, color: rowColor }) => ({ label, value, color: rowColor }));
}
