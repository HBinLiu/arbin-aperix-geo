import { useCallback, useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TooltipProps } from "recharts";

import { ChartMetricTooltipPanel } from "@/components/analysis/common/ChartChrome";
import { formatChartDayLabel, formatChartTooltipDate, type SingleSeriesPoint } from "@/lib/analysis/chart";
import { formatRankMetric } from "@/lib/analysis/format";
import { cn } from "@/lib/utils";

type AverageRankBarChartProps = {
  series?: SingleSeriesPoint[];
  className?: string;
  height?: number;
};

const BAR_COLOR = "#ec4899";
const RANK_TOOLTIP_LABEL = "平均排名";
const HOVER_CURSOR_FILL = "rgba(0,0,0,0.08)";
const AXIS_TICK = { fill: "#9ca3af", fontSize: 13 };
const GRID_STROKE = "#e4e4e4";

type BarTooltipPayload = {
  date?: string;
};

export function AverageRankBarChart({ series = [], className, height }: AverageRankBarChartProps) {
  const data = useMemo(
    () =>
      series.map((pt) => ({
        date: pt.date,
        dateLabel: formatChartDayLabel(pt.date),
        value: pt.value,
      })),
    [series],
  );

  const maxRank = useMemo(() => {
    const values = data.map((d) => d.value).filter((v): v is number => v != null);
    if (values.length === 0) return 5;
    return Math.max(5, Math.ceil(Math.max(...values)));
  }, [data]);

  const tooltipContent = useCallback(({ active, payload }: TooltipProps<number, string>) => {
    if (!active || !payload?.length) return null;

    const row = payload[0]?.payload as BarTooltipPayload | undefined;
    const date = row?.date ?? "";
    const value = payload[0]?.value;

    return (
      <ChartMetricTooltipPanel
        header={date ? formatChartTooltipDate(date) : undefined}
        rows={[
          {
            label: RANK_TOOLTIP_LABEL,
            value: formatRankMetric(typeof value === "number" ? value : null),
            color: BAR_COLOR,
          },
        ]}
      />
    );
  }, []);

  const fixedHeight = height != null;

  if (data.length === 0) {
    return (
      <div
        className={cn(
          "text-muted-foreground flex items-center justify-center text-sm",
          !fixedHeight && "min-h-[120px] flex-1",
          className,
        )}
        style={fixedHeight ? { height } : { minHeight: 120 }}
      >
        暂无数据
      </div>
    );
  }

  return (
    <div
      className={cn("min-h-0 w-full", !fixedHeight && "min-h-[120px] flex-1", className)}
      style={fixedHeight ? { height } : undefined}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={GRID_STROKE} vertical={false} />
          <XAxis
            dataKey="dateLabel"
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={{ stroke: GRID_STROKE }}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={false}
            width={28}
            domain={[0, maxRank]}
            allowDecimals
          />
          <Tooltip
            content={tooltipContent}
            cursor={{ fill: HOVER_CURSOR_FILL }}
            wrapperStyle={{ outline: "none", zIndex: 10 }}
          />
          <Bar
            dataKey="value"
            fill={BAR_COLOR}
            activeBar={{ fill: BAR_COLOR }}
            radius={[4, 4, 0, 0]}
            maxBarSize={32}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
