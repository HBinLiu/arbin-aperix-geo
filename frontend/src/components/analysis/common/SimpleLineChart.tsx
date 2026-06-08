import { useCallback, useMemo } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TooltipProps } from "recharts";

import {
  buildChartModel,
  buildChartTooltipRows,
  CHART_COLORS,
  CHART_HEIGHT,
  formatChartTooltipDate,
  type ChartLegendItem,
  type MultiSeriesPoint,
  type SingleSeriesPoint,
} from "@/lib/analysis/chart";
import { formatRate } from "@/lib/analysis/format";
import { cn } from "@/lib/utils";

export { CHART_COLORS, CHART_HEIGHT };

type SimpleLineChartProps = {
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
  className?: string;
  height?: number;
};

const AXIS_TICK = { fill: "#9ca3af", fontSize: 13 };
const GRID_STROKE = "#e4e4e4";

function LegendSwatch({ color, muted }: { color: string; muted?: boolean }) {
  return (
    <span
      className={cn(
        "inline-block size-2 shrink-0 rounded-[2px]",
        muted && "bg-muted-foreground/35",
      )}
      style={muted ? undefined : { backgroundColor: color }}
      aria-hidden
    />
  );
}

function ChartLegendContent({ items }: { items: ChartLegendItem[] }) {
  if (items.length === 0) return null;

  return (
    <div className="flex w-full min-w-0 flex-wrap items-center justify-center gap-x-3 gap-y-1.5 pt-1 text-xs leading-none">
      {items.map((item) => {
        const content = (
          <>
            <LegendSwatch color={item.color} muted={!item.visible} />
            <span
              className={cn(
                "whitespace-nowrap font-medium",
                item.visible ? "text-foreground" : "text-muted-foreground",
              )}
            >
              {item.label}
            </span>
          </>
        );

        if (item.interactive && item.onToggle) {
          return (
            <button
              key={item.key}
              type="button"
              onClick={item.onToggle}
              className="inline-flex cursor-pointer items-center gap-1.5"
            >
              {content}
            </button>
          );
        }

        return (
          <span key={item.key} className="inline-flex items-center gap-1.5">
            {content}
          </span>
        );
      })}
    </div>
  );
}

type ChartTooltipProps = TooltipProps<number, string> & {
  labels: string[];
  hiddenLegendKeys?: Set<string>;
  overlayPrevious: boolean;
  previousSeries?: MultiSeriesPoint[];
  showCurrentSeries?: boolean;
  showPreviousSeries?: boolean;
  valueFormatter: (v: number) => string;
};

function ChartTooltip({
  active,
  payload,
  labels,
  hiddenLegendKeys,
  overlayPrevious,
  previousSeries,
  showCurrentSeries,
  showPreviousSeries,
  valueFormatter,
}: ChartTooltipProps) {
  if (!active || !payload?.length) return null;

  const date = String(payload[0]?.payload?.date ?? "");
  const valuesByKey = Object.fromEntries(
    payload.map((entry) => [String(entry.dataKey), Number(entry.value ?? 0)]),
  );
  const rows = buildChartTooltipRows({
    valuesByKey,
    labels,
    hiddenLegendKeys,
    overlayPrevious,
    previousSeries,
    showCurrentSeries,
    showPreviousSeries,
    valueFormatter,
  });

  if (rows.length === 0) return null;

  return (
    <div className="border-border pointer-events-none min-w-[9rem] rounded-md border bg-white px-2 py-2 shadow-md">
      <p className="text-foreground mb-1 text-xs font-semibold">{formatChartTooltipDate(date)}</p>
      <ul className="space-y-1">
        {rows.map((row) => (
          <li key={row.label} className="flex items-center justify-between gap-4 text-xs">
            <span className="inline-flex min-w-0 items-center gap-1">
              <span
                className="inline-block size-2 shrink-0 rounded-[2px]"
                style={{ backgroundColor: row.color }}
                aria-hidden
              />
              <span className="text-muted-foreground truncate">{row.label}</span>
            </span>
            <span className="text-foreground shrink-0 font-medium tabular-nums">{row.value}</span>
          </li>
        ))}
      </ul>
    </div>
  );
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
  className,
  height = CHART_HEIGHT,
}: SimpleLineChartProps) {
  const fixedHeight = height != null;
  const chartHeight = fixedHeight ? height : CHART_HEIGHT;

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

  const showLegend = model.legendItems.length > 0;

  const tooltipContent = useCallback(
    (props: TooltipProps<number, string>) => (
      <ChartTooltip
        {...props}
        labels={labels}
        hiddenLegendKeys={hiddenLegendKeys}
        overlayPrevious={overlayPrevious}
        previousSeries={previousSeries}
        showCurrentSeries={showCurrentSeries}
        showPreviousSeries={showPreviousSeries}
        valueFormatter={valueFormatter}
      />
    ),
    [
      labels,
      hiddenLegendKeys,
      overlayPrevious,
      previousSeries,
      showCurrentSeries,
      showPreviousSeries,
      valueFormatter,
    ],
  );

  const legendContent = useCallback(
    () => <ChartLegendContent items={model.legendItems} />,
    [model.legendItems],
  );

  const rootStyle = fixedHeight ? { height: chartHeight, minHeight: chartHeight } : undefined;
  const plotAreaClass = fixedHeight ? "shrink-0 w-full" : "min-h-0 flex-1";

  if (model.rows.length === 0 || model.lines.length === 0) {
    return (
      <div className={cn("flex w-full min-w-0 flex-col", className)} style={rootStyle}>
        <div
          className={cn(
            "text-muted-foreground flex h-full items-center justify-center text-sm",
            plotAreaClass,
          )}
        >
          暂无数据
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex w-full min-w-0 flex-col", className)} style={rootStyle}>
      <div className={cn("min-h-0 h-full w-full", plotAreaClass)}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={model.rows} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
            <CartesianGrid vertical={false} stroke={GRID_STROKE} strokeDasharray="4 4" />
            <XAxis
              dataKey="dateLabel"
              axisLine={false}
              tickLine={false}
              tick={AXIS_TICK}
              interval="preserveStartEnd"
              dy={8}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={AXIS_TICK}
              width={model.yAxisWidth}
              domain={[0, model.yMax]}
              ticks={model.yTicks}
              tickFormatter={(value) => valueFormatter(Number(value))}
            />
            <Tooltip
              cursor={{ stroke: GRID_STROKE, strokeWidth: 1 }}
              content={tooltipContent}
              wrapperStyle={{ outline: "none", zIndex: 10 }}
            />
            {showLegend ? (
              <Legend
                verticalAlign="bottom"
                align="center"
                content={legendContent}
                wrapperStyle={{ width: "100%", left: 0, paddingTop: 6 }}
              />
            ) : null}
            {model.lines.map((line) => (
              <Line
                key={line.key}
                name={line.key}
                type="linear"
                dataKey={line.key}
                stroke={line.color}
                strokeWidth={2}
                strokeDasharray={line.dashed ? "5 4" : undefined}
                dot={false}
                activeDot={{
                  r: 4,
                  stroke: "#fff",
                  strokeWidth: 2,
                  fill: line.color,
                }}
                animationDuration={600}
                animationEasing="ease-out"
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
