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
import { PlatformLogo } from "@/components/brand/PlatformLogo";
import { computeChartYAxisWidth } from "@/lib/analysis/chart";
import { formatRankMetric } from "@/lib/analysis/format";
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
const HOVER_CURSOR_FILL = "rgba(0,0,0,0.08)";
const AXIS_TICK = { fill: "#9ca3af", fontSize: 13 };
const GRID_STROKE = "#e4e4e4";

const RATE_Y_TICKS = [0, 0.25, 0.5, 0.75, 1] as const;

type BarTooltipPayload = {
  platform?: string;
  label?: string;
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

  const yTickFormatter = useCallback(
    (value: number) =>
      metric.yAxisMode === "rate" ? `${Math.round(value * 100)}%` : formatRankMetric(value),
    [metric.yAxisMode],
  );

  const yMax = useMemo(() => {
    if (metricId === "averageRank") {
      const values = data.map((row) => row.value).filter((v): v is number => v != null);
      if (values.length === 0) return 5;
      return Math.max(5, Math.ceil(Math.max(...values)));
    }
    return 1;
  }, [data, metricId]);

  const yAxisWidth = useMemo(() => {
    if (metric.yAxisMode === "rate") {
      const labels = RATE_Y_TICKS.map((value) => yTickFormatter(value));
      const longest = Math.max(...labels.map((label) => label.length), 0);
      return Math.max(36, longest * 8 + 8);
    }
    return computeChartYAxisWidth(0, yMax, yTickFormatter);
  }, [yMax, yTickFormatter, metric.yAxisMode]);

  const tooltipContent = useCallback(
    ({ active, payload }: TooltipProps<number, string>) => {
      if (!active || !payload?.length) return null;

      const row = payload[0]?.payload as BarTooltipPayload | undefined;
      const value = payload[0]?.value;

      return (
        <ChartMetricTooltipPanel
          header={metric.label}
          rows={[
            {
              label: row?.label ?? "",
              value: metric.formatValue(typeof value === "number" ? value : null),
              icon:
                row?.platform != null ? (
                  <PlatformLogo
                    provider={row.platform}
                    label={row.label ?? row.platform}
                    className="size-4 rounded-sm"
                  />
                ) : undefined,
            },
          ]}
        />
      );
    },
    [metric],
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

  const yDomain: [number, number] = [0, yMax];

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
            width={yAxisWidth}
            domain={yDomain}
            ticks={metric.yAxisMode === "rate" ? [...RATE_Y_TICKS] : undefined}
            tickCount={metric.yAxisMode === "rate" ? undefined : 5}
            allowDecimals={metricId === "averageRank"}
            tickFormatter={yTickFormatter}
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
            maxBarSize={40}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
