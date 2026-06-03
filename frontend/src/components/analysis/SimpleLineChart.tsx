import { useMemo } from "react";

import { cn } from "@/lib/utils";

export const CHART_COLORS = [
  "#ec4899",
  "#3b82f6",
  "#14b8a6",
  "#f97316",
  "#8b5cf6",
  "#64748b",
];

type SeriesPoint = {
  date: string;
  values: Record<string, number>;
};

type SingleSeriesPoint = {
  date: string;
  value: number | null;
};

type SimpleLineChartProps = {
  multiSeries?: SeriesPoint[];
  singleSeries?: SingleSeriesPoint[];
  labels?: string[];
  visibleLabels?: Set<string>;
  compareSeries?: SeriesPoint[];
  showCompare?: boolean;
  valueFormatter?: (v: number) => string;
  className?: string;
};

const PAD = { top: 16, right: 12, bottom: 28, left: 36 };
const W = 560;
const H = 300;

function formatDayLabel(iso: string): string {
  const d = new Date(iso);
  return `${d.getMonth() + 1}月${d.getDate()}日`;
}

function buildPath(
  points: { x: number; y: number }[],
): string {
  if (points.length === 0) return "";
  return points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
}

export function SimpleLineChart({
  multiSeries,
  singleSeries,
  labels = [],
  visibleLabels,
  compareSeries,
  showCompare = false,
  valueFormatter = (v) => `${(v * 100).toFixed(1)}%`,
  className,
}: SimpleLineChartProps) {
  const chart = useMemo(() => {
    const dates =
      multiSeries?.map((p) => p.date) ??
      singleSeries?.map((p) => p.date) ??
      [];

    if (dates.length === 0) return null;

    const activeLabels = labels.filter((l) => !visibleLabels || visibleLabels.has(l));

    let maxVal = 0.01;
    if (multiSeries) {
      for (const pt of multiSeries) {
        for (const lab of activeLabels) {
          maxVal = Math.max(maxVal, pt.values[lab] ?? 0);
        }
      }
      if (showCompare && compareSeries) {
        for (const pt of compareSeries) {
          for (const lab of activeLabels) {
            maxVal = Math.max(maxVal, pt.values[lab] ?? 0);
          }
        }
      }
    } else if (singleSeries) {
      for (const pt of singleSeries) {
        if (pt.value != null) maxVal = Math.max(maxVal, pt.value);
      }
    }
    maxVal = Math.max(maxVal * 1.15, 0.05);

    const innerW = W - PAD.left - PAD.right;
    const innerH = H - PAD.top - PAD.bottom;
    const xAt = (i: number) => PAD.left + (dates.length <= 1 ? innerW / 2 : (i / (dates.length - 1)) * innerW);
    const yAt = (v: number) => PAD.top + innerH - (v / maxVal) * innerH;

    const lines: { label: string; path: string; color: string; dashed?: boolean }[] = [];

    if (multiSeries && activeLabels.length > 0) {
      activeLabels.forEach((lab, idx) => {
        const pts = multiSeries
          .map((p, i) => ({ x: xAt(i), y: yAt(p.values[lab] ?? 0) }));
        lines.push({
          label: lab,
          path: buildPath(pts),
          color: CHART_COLORS[idx % CHART_COLORS.length],
        });
      });
      if (showCompare && compareSeries) {
        activeLabels.forEach((lab, idx) => {
          const pts = compareSeries.map((p, i) => ({
            x: xAt(Math.min(i, dates.length - 1)),
            y: yAt(p.values[lab] ?? 0),
          }));
          lines.push({
            label: `${lab}（上周期）`,
            path: buildPath(pts),
            color: CHART_COLORS[idx % CHART_COLORS.length],
            dashed: true,
          });
        });
      }
    } else if (singleSeries) {
      const pts = singleSeries
        .filter((p) => p.value != null)
        .map((p, i) => ({ x: xAt(i), y: yAt(p.value!) }));
      lines.push({
        label: "当前",
        path: buildPath(pts),
        color: CHART_COLORS[0],
      });
    }

    const yTicks = [0, maxVal / 2, maxVal].map((v) => ({
      y: yAt(v),
      label: valueFormatter(v),
    }));

    return { dates, lines, yTicks, xAt, innerH, maxVal };
  }, [
    multiSeries,
    singleSeries,
    labels,
    visibleLabels,
    compareSeries,
    showCompare,
    valueFormatter,
  ]);

  if (!chart) {
    return (
      <div className={cn("text-muted-foreground flex h-[300px] items-center justify-center text-sm", className)}>
        暂无数据
      </div>
    );
  }

  return (
    <div className={cn("w-full", className)}>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="趋势折线图">
        {chart.yTicks.map((t) => (
          <g key={t.label}>
            <line
              x1={PAD.left}
              x2={W - PAD.right}
              y1={t.y}
              y2={t.y}
              className="stroke-border"
              strokeWidth={1}
              strokeDasharray="4 4"
            />
            <text
              x={PAD.left - 6}
              y={t.y + 4}
              textAnchor="end"
              className="fill-muted-foreground text-[10px] tabular-nums"
            >
              {t.label}
            </text>
          </g>
        ))}
        {chart.lines.map((line) => (
          <path
            key={line.label + line.path}
            d={line.path}
            fill="none"
            stroke={line.color}
            strokeWidth={2}
            strokeDasharray={line.dashed ? "5 4" : undefined}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ))}
        {chart.dates.map((d, i) => (
          <text
            key={d}
            x={chart.xAt(i)}
            y={H - 6}
            textAnchor="middle"
            className="fill-muted-foreground text-[10px]"
          >
            {formatDayLabel(d)}
          </text>
        ))}
      </svg>
    </div>
  );
}
