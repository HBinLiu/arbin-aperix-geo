import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatChartDayLabel, formatChartTooltipDate, type SingleSeriesPoint } from "@/lib/analysis/chart";
import { cn } from "@/lib/utils";

type AverageRankBarChartProps = {
  series?: SingleSeriesPoint[];
  className?: string;
  height?: number;
};

const BAR_COLOR = "#ec4899";
const AXIS_TICK = { fill: "#9ca3af", fontSize: 13 };
const GRID_STROKE = "#e4e4e4";

const TOOLTIP_STYLE = {
  fontSize: 13,
  borderRadius: 8,
  border: "1px solid #e5e7eb",
  boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
};

export function AverageRankBarChart({ series = [], className, height = 220 }: AverageRankBarChartProps) {
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

  if (data.length === 0) {
    return (
      <div
        className={cn("text-muted-foreground flex items-center justify-center text-sm", className)}
        style={{ height }}
      >
        暂无数据
      </div>
    );
  }

  return (
    <div className={cn("min-h-0 w-full", className)} style={{ height }}>
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
            labelFormatter={(_, payload) => {
              const row = payload?.[0]?.payload as { date?: string } | undefined;
              return row?.date ? formatChartTooltipDate(row.date) : "";
            }}
            formatter={(value: number) => [value.toFixed(1), "平均排名"]}
            contentStyle={TOOLTIP_STYLE}
          />
          <Bar dataKey="value" fill={BAR_COLOR} radius={[4, 4, 0, 0]} maxBarSize={32} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
