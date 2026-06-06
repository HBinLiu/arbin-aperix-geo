import { useMemo } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { CHART_COLORS, colorOfChartLabel } from "@/lib/analysis/chart";
import { formatRate } from "@/lib/analysis/format";
import { cn } from "@/lib/utils";

export type ShareVoiceSlice = {
  label: string;
  value: number;
};

type ShareVoiceDonutChartProps = {
  slices: ShareVoiceSlice[];
  className?: string;
  height?: number;
};

const TOOLTIP_STYLE = {
  fontSize: 13,
  borderRadius: 8,
  border: "1px solid #e5e7eb",
  boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
};

export function ShareVoiceDonutChart({
  slices,
  className,
  height = 220,
}: ShareVoiceDonutChartProps) {
  const labels = useMemo(() => slices.map((s) => s.label), [slices]);
  const data = useMemo(
    () =>
      slices
        .filter((s) => s.value > 0)
        .map((s) => ({
          name: s.label,
          value: s.value,
          color: colorOfChartLabel(labels, s.label),
        })),
    [labels, slices],
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
    <div className={cn("flex min-h-0 flex-col", className)}>
      <div className="min-h-0 w-full" style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius="58%"
              outerRadius="82%"
              paddingAngle={1}
              stroke="#fff"
              strokeWidth={2}
            >
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number) => formatRate(value)}
              contentStyle={TOOLTIP_STYLE}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="mt-3 flex flex-wrap justify-center gap-x-4 gap-y-2 px-2">
        {slices.map((slice, index) => (
          <li key={slice.label} className="inline-flex items-center gap-1.5 text-xs">
            <span
              className="size-2.5 shrink-0 rounded-sm"
              style={{ backgroundColor: colorOfChartLabel(labels, slice.label) || CHART_COLORS[index % CHART_COLORS.length] }}
            />
            <span className="text-muted-foreground">{slice.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
