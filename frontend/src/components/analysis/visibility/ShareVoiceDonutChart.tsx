import { useCallback, useMemo } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { TooltipProps } from "recharts";

import {
  ChartEmptyState,
  ChartLegendList,
  ChartMetricTooltipPanel,
} from "@/components/analysis/common/ChartChrome";
import {
  buildChartColorLookup,
  chartColorFromLookup,
} from "@/lib/analysis/chart";
import { formatRate } from "@/lib/analysis/format";
import { cn } from "@/lib/utils";

export type ShareVoiceSlice = {
  label: string;
  value: number;
  /** 与折线图 entity 目录顺序对齐，用于配色 */
  colorKey?: string;
};

type ShareVoiceDonutChartProps = {
  slices: ShareVoiceSlice[];
  className?: string;
  height?: number;
};

type PieTooltipPayload = {
  color?: string;
};

export function ShareVoiceDonutChart({
  slices,
  className,
  height,
}: ShareVoiceDonutChartProps) {
  const fixedHeight = height != null;
  const labels = useMemo(
    () => slices.map((s) => s.colorKey?.trim() || s.label),
    [slices],
  );
  const colorLookup = useMemo(() => buildChartColorLookup(labels), [labels]);

  const data = useMemo(
    () =>
      slices.map((s) => {
        const colorKey = s.colorKey?.trim() || s.label;
        return {
          name: s.label,
          value: s.value,
          color: chartColorFromLookup(colorLookup, colorKey),
        };
      }),
    [colorLookup, slices],
  );

  const legendItems = useMemo(
    () =>
      slices.map((slice) => {
        const colorKey = slice.colorKey?.trim() || slice.label;
        return {
          label: slice.label,
          color: chartColorFromLookup(colorLookup, colorKey),
        };
      }),
    [colorLookup, slices],
  );

  const tooltipContent = useCallback(({ active, payload }: TooltipProps<number, string>) => {
    if (!active || !payload?.length) return null;

    const entry = payload[0];
    const label = String(entry.name ?? "");
    const value = Number(entry.value ?? 0);
    const color =
      (entry.payload as PieTooltipPayload | undefined)?.color ??
      chartColorFromLookup(colorLookup, label);

    return (
      <ChartMetricTooltipPanel
        rows={[{ label, value: formatRate(value), color }]}
      />
    );
  }, [colorLookup]);

  const hasPositiveSlice = data.some((s) => s.value > 0);

  if (!hasPositiveSlice) {
    return (
      <ChartEmptyState
        className={cn(!fixedHeight && "min-h-[120px] flex-1", className)}
        style={fixedHeight ? { height } : { minHeight: 120 }}
      />
    );
  }

  const pieData = data.filter((s) => s.value > 0);

  return (
    <div
      className={cn(
        "flex min-h-0 flex-col",
        !fixedHeight && "min-h-[120px] flex-1",
        className,
      )}
      style={fixedHeight ? { height, minHeight: height } : undefined}
    >
      <div className="min-h-0 w-full flex-1">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={pieData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius="58%"
              outerRadius="78%"
              paddingAngle={1}
              stroke="#fff"
              strokeWidth={2}
            >
              {pieData.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip content={tooltipContent} wrapperStyle={{ outline: "none", zIndex: 10 }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ChartLegendList items={legendItems} className="shrink-0 pt-1" />
    </div>
  );
}
