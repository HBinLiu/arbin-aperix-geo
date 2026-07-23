import { useCallback, useId, useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TooltipProps } from "recharts";

import {
  ChartEmptyState,
  ChartLegendContent,
  ChartTooltip,
  CHART_GRID_STROKE,
} from "@/components/analysis/common/ChartChrome";
import {
  buildChartModel,
  chartDisplayLabel,
  CHART_HEIGHT,
  type MultiSeriesPoint,
  type SingleSeriesPoint,
} from "@/lib/analysis/chart";
import { useChartDateAxisLayout } from "@/hooks/useChartDateAxisLayout";
import { formatRate } from "@/lib/analysis/format";
import { cn } from "@/lib/utils";

export { CHART_HEIGHT };

export type SimpleLineChartProps = {
  multiSeries?: MultiSeriesPoint[];
  singleSeries?: SingleSeriesPoint[];
  labels?: string[];
  hiddenLegendKeys?: Set<string>;
  onToggleLegendKey?: (key: string) => void;
  previousSeries?: MultiSeriesPoint[];
  overlayPrevious?: boolean;
  showCurrentSeries?: boolean;
  showPreviousSeries?: boolean;
  valueFormatter?: (v: number) => string;
  yAxisMode?: "rate" | "score";
  variant?: "line" | "area";
  /** 单序列 tooltip 标签（如「引用次数」） */
  tooltipLabel?: string;
  /** series key → 展示名（brand 优先，否则 domain）；不传则沿用 key */
  legendLabels?: Record<string, string>;
  className?: string;
  height?: number;
};

const AXIS_TICK = { fill: "#9ca3af", fontSize: 13 };
const CHART_MARGIN = { top: 8, right: 8, left: 0, bottom: 4 };
const ACTIVE_DOT = { r: 4, stroke: "var(--surface)", strokeWidth: 2 };

function gradientDomId(prefix: string, key: string): string {
  let hash = 0;
  for (let i = 0; i < key.length; i++) {
    hash = (hash * 31 + key.charCodeAt(i)) >>> 0;
  }
  return `${prefix}-${hash}`;
}

export function SimpleLineChart({
  multiSeries,
  singleSeries,
  labels = [],
  hiddenLegendKeys,
  onToggleLegendKey,
  previousSeries,
  overlayPrevious = false,
  showCurrentSeries = true,
  showPreviousSeries = true,
  valueFormatter = formatRate,
  yAxisMode = "rate",
  variant = "line",
  tooltipLabel,
  legendLabels,
  className,
  height,
}: SimpleLineChartProps) {
  const gradientId = useId().replace(/:/g, "");
  const fixedHeight = height != null;
  const chartHeight = height ?? CHART_HEIGHT;
  const ChartComponent = variant === "area" ? AreaChart : LineChart;

  const model = useMemo(
    () =>
      buildChartModel({
        multiSeries,
        singleSeries,
        previousSeries,
        labels,
        hiddenLegendKeys,
        overlayPrevious,
        showCurrentSeries,
        showPreviousSeries,
        onToggleLegendKey,
        valueFormatter,
        yAxisMode,
      }),
    [
      multiSeries,
      singleSeries,
      previousSeries,
      labels,
      hiddenLegendKeys,
      overlayPrevious,
      showCurrentSeries,
      showPreviousSeries,
      onToggleLegendKey,
      valueFormatter,
      yAxisMode,
    ],
  );

  const legendItems = useMemo(
    () =>
      model.legendItems.map((item) => ({
        ...item,
        label: chartDisplayLabel(item.key, legendLabels, item.label),
      })),
    [model.legendItems, legendLabels],
  );

  const tooltipContent = useCallback(
    (props: TooltipProps<number, string>) => (
      <ChartTooltip
        active={props.active}
        payload={props.payload}
        model={model}
        valueFormatter={valueFormatter}
        tooltipLabel={tooltipLabel}
        legendLabels={legendLabels}
      />
    ),
    [model, valueFormatter, tooltipLabel, legendLabels],
  );

  const { plotRef, xAxisLayout } = useChartDateAxisLayout({
    pointCount: model.rows.length,
    yAxisWidth: model.yAxisWidth,
    marginLeft: CHART_MARGIN.left,
    marginRight: CHART_MARGIN.right,
  });

  const legendHeight = legendItems.length > 0 ? 44 : 0;
  const plotHeight = fixedHeight ? Math.max(chartHeight - legendHeight, 120) : undefined;
  const rootStyle = fixedHeight ? { height: chartHeight, minHeight: chartHeight } : undefined;

  if (model.rows.length === 0 || model.lines.length === 0) {
    return (
      <div
        className={cn(
          "flex w-full min-w-0 flex-col",
          !fixedHeight && "min-h-0 flex-1",
          className,
        )}
        style={rootStyle}
      >
        <ChartEmptyState
          className={cn(!fixedHeight && "min-h-0 flex-1")}
          style={fixedHeight ? { height: chartHeight, minHeight: chartHeight } : undefined}
        />
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex w-full min-w-0 flex-col",
        fixedHeight ? "h-full" : "min-h-0 flex-1",
        className,
      )}
      style={rootStyle}
    >
      <div
        ref={plotRef}
        className={cn("w-full", fixedHeight ? "min-h-0 shrink-0" : "min-h-[120px] flex-1")}
        style={plotHeight != null ? { height: plotHeight } : undefined}
      >
        <ResponsiveContainer width="100%" height={plotHeight ?? "100%"}>
          <ChartComponent data={model.rows} margin={CHART_MARGIN}>
            {variant === "area" ? (
              <defs>
                {model.lines.map((line) => {
                  const fillId = gradientDomId(gradientId, line.key);
                  return (
                    <linearGradient key={fillId} id={fillId} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={line.color} stopOpacity={0.28} />
                      <stop offset="100%" stopColor={line.color} stopOpacity={0.02} />
                    </linearGradient>
                  );
                })}
              </defs>
            ) : null}
            <CartesianGrid vertical={false} stroke={CHART_GRID_STROKE} strokeDasharray="4 4" />
            <XAxis
              dataKey="date"
              axisLine={false}
              tickLine={false}
              tick={AXIS_TICK}
              minTickGap={xAxisLayout.minTickGap}
              tickFormatter={xAxisLayout.formatTick}
              dy={8}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={AXIS_TICK}
              width={model.yAxisWidth}
              domain={[model.yMin, model.yMax]}
              tickCount={5}
              allowDecimals
              tickFormatter={(value) => valueFormatter(Number(value))}
            />
            <Tooltip
              cursor={{ stroke: CHART_GRID_STROKE, strokeWidth: 1 }}
              content={tooltipContent}
              wrapperStyle={{ outline: "none", zIndex: 10 }}
            />
            {model.lines.map((line) =>
              variant === "area" ? (
                <Area
                  key={line.key}
                  name={line.key}
                  type="basis"
                  dataKey={line.key}
                  stroke={line.color}
                  strokeWidth={2}
                  fill={`url(#${gradientDomId(gradientId, line.key)})`}
                  dot={false}
                  activeDot={{ ...ACTIVE_DOT, fill: line.color }}
                  isAnimationActive={false}
                />
              ) : (
                <Line
                  key={line.key}
                  name={line.key}
                  type="monotone"
                  dataKey={line.key}
                  stroke={line.color}
                  strokeWidth={2}
                  strokeDasharray={line.dashed ? "5 4" : undefined}
                  dot={model.rows.length <= 1}
                  activeDot={{ ...ACTIVE_DOT, fill: line.color }}
                  isAnimationActive={false}
                />
              ),
            )}
          </ChartComponent>
        </ResponsiveContainer>
      </div>
      {legendItems.length > 0 ? (
        <div className="shrink-0 pt-1">
          <ChartLegendContent items={legendItems} />
        </div>
      ) : null}
    </div>
  );
}
