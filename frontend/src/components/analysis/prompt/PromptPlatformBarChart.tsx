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

import { resolvePlatformMeta } from "@/lib/analysis/shared";
import {
  platformMetricValue,
  promptDetailMetric,
  type PromptDetailMetricId,
} from "@/lib/analysis/promptDetail";
import type { PlatformPerformance, SamplingPlatform } from "@/types";
import { cn } from "@/lib/utils";

type PromptPlatformBarChartProps = {
  platforms: PlatformPerformance[];
  platformsMeta: SamplingPlatform[];
  metricId: PromptDetailMetricId;
  className?: string;
  height?: number;
};

const BAR_COLOR = "#6366f1";
const AXIS_TICK = { fill: "#9ca3af", fontSize: 13 };
const GRID_STROKE = "#e4e4e4";

const TOOLTIP_STYLE = {
  fontSize: 13,
  borderRadius: 8,
  border: "1px solid #e5e7eb",
  boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
};

/** 提示词详情 · 按平台柱状图 */
export function PromptPlatformBarChart({
  platforms,
  platformsMeta,
  metricId,
  className,
  height = 270,
}: PromptPlatformBarChartProps) {
  const metric = promptDetailMetric(metricId);

  const data = useMemo(
    () =>
      platforms.map((row) => {
        const meta = resolvePlatformMeta(row.platform, platformsMeta);
        return {
          platform: row.platform,
          label: meta.label,
          value: platformMetricValue(row, metricId),
        };
      }),
    [platforms, platformsMeta, metricId],
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

  const yDomain: [number, number | "auto"] =
    metricId === "averageRank" ? [0, "auto"] : [0, 1];

  return (
    <div className={cn("min-h-0 w-full", className)} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={GRID_STROKE} vertical={false} />
          <XAxis
            dataKey="label"
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={{ stroke: GRID_STROKE }}
            interval={0}
          />
          <YAxis
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={false}
            width={36}
            domain={yDomain}
            tickFormatter={(value: number) =>
              metric.yAxisMode === "rate" ? `${Math.round(value * 100)}%` : String(value)
            }
          />
          <Tooltip
            formatter={(value: number) => [metric.formatValue(value), metric.label]}
            contentStyle={TOOLTIP_STYLE}
          />
          <Bar dataKey="value" fill={BAR_COLOR} radius={[4, 4, 0, 0]} maxBarSize={40} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
