import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatChartDayLabel, formatChartTooltipDate } from "@/lib/analysis/chart";
import { formatRate } from "@/lib/analysis/format";
import type { SentimentDistributionPoint } from "@/types";
import { cn } from "@/lib/utils";

const POSITIVE_COLOR = "#22c55e";
const NEUTRAL_COLOR = "#f97316";
const NEGATIVE_COLOR = "#ef4444";
const AXIS_TICK = { fill: "#9ca3af", fontSize: 13 };
const GRID_STROKE = "#e4e4e4";

type SentimentDistributionChartProps = {
  series?: SentimentDistributionPoint[];
  className?: string;
  height?: number;
};

type ChartRow = SentimentDistributionPoint & {
  dateLabel: string;
};

function ChartLegendContent() {
  const items = [
    { label: "正面", color: POSITIVE_COLOR },
    { label: "中立", color: NEUTRAL_COLOR },
    { label: "负面", color: NEGATIVE_COLOR },
  ];

  return (
    <div className="flex w-full min-w-0 flex-wrap items-center justify-center gap-x-4 gap-y-1.5 pt-1 text-xs leading-none">
      {items.map((item) => (
        <span key={item.label} className="inline-flex items-center gap-1.5">
          <span
            className="inline-block size-2 shrink-0 rounded-[2px]"
            style={{ backgroundColor: item.color }}
            aria-hidden
          />
          <span className="text-foreground whitespace-nowrap font-medium">{item.label}</span>
        </span>
      ))}
    </div>
  );
}

export function SentimentDistributionChart({
  series = [],
  className,
  height = 270,
}: SentimentDistributionChartProps) {
  const data = useMemo<ChartRow[]>(
    () =>
      series.map((point) => ({
        ...point,
        dateLabel: formatChartDayLabel(point.date),
      })),
    [series],
  );

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
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
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
            width={44}
            domain={[0, 1]}
            ticks={[0, 0.25, 0.5, 0.75, 1]}
            tickFormatter={(value) => formatRate(Number(value))}
          />
          <Tooltip
            cursor={{ fill: "rgba(0,0,0,0.04)" }}
            labelFormatter={(_, payload) => {
              const row = payload?.[0]?.payload as ChartRow | undefined;
              return row?.date ? formatChartTooltipDate(row.date) : "";
            }}
            formatter={(value: number, name: string) => [
              formatRate(value),
              name === "positive" ? "正面" : name === "neutral" ? "中立" : "负面",
            ]}
            contentStyle={{
              fontSize: 13,
              borderRadius: 8,
              border: "1px solid #e5e7eb",
              boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
            }}
          />
          <Legend verticalAlign="bottom" align="center" content={<ChartLegendContent />} />
          <Bar dataKey="positive" stackId="sentiment" fill={POSITIVE_COLOR} maxBarSize={40} />
          <Bar dataKey="neutral" stackId="sentiment" fill={NEUTRAL_COLOR} maxBarSize={40} />
          <Bar dataKey="negative" stackId="sentiment" fill={NEGATIVE_COLOR} maxBarSize={40} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
