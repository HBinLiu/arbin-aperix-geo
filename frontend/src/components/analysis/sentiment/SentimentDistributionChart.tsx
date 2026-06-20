import { useCallback, useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TooltipProps } from "recharts";

import { ChartMetricTooltipPanel } from "@/components/analysis/common/ChartChrome";
import { PlatformLogo } from "@/components/brand/PlatformLogo";
import { formatChartDayLabel, formatChartTooltipDate } from "@/lib/analysis/chart";
import { formatSentimentScore } from "@/lib/analysis/format";
import { SENTIMENT_BAR_COLORS } from "@/lib/analysis/sentiment";
import { resolvePlatformMeta } from "@/lib/analysis/shared";
import type { SamplingPlatform, SentimentDistributionPoint, SentimentTab } from "@/types";
import { cn } from "@/lib/utils";

const Y_TICKS = [0, 25, 50, 75, 100] as const;
const AXIS_TICK = { fill: "#9ca3af", fontSize: 13 };
const GRID_STROKE = "#e4e4e4";
const HOVER_CURSOR_FILL = "rgba(0,0,0,0.04)";

type SentimentDistributionChartProps = {
  series?: SentimentDistributionPoint[];
  platformsMeta?: SamplingPlatform[];
  className?: string;
};

type ChartRow = SentimentDistributionPoint & {
  dateLabel: string;
  score: number;
};

function barColor(label: SentimentTab | string | undefined): string {
  if (label === "positive" || label === "negative" || label === "neutral") {
    return SENTIMENT_BAR_COLORS[label];
  }
  return SENTIMENT_BAR_COLORS.neutral;
}

function sortedPlatformTooltipRows(
  platformScores: Record<string, number>,
  platformsMeta: SamplingPlatform[],
): Array<{ platformId: string; score: number }> {
  const platformIds =
    platformsMeta.length > 0
      ? platformsMeta.map((platform) => platform.platform)
      : Object.keys(platformScores);

  return platformIds
    .map((platformId) => ({
      platformId,
      score: platformScores[platformId] ?? 0,
    }))
    .sort((a, b) => b.score - a.score);
}

export function SentimentDistributionChart({
  series = [],
  platformsMeta = [],
  className,
}: SentimentDistributionChartProps) {
  const data = useMemo<ChartRow[]>(
    () =>
      series.map((point) => ({
        ...point,
        dateLabel: formatChartDayLabel(point.date),
        score: point.sentiment_score ?? 0,
      })),
    [series],
  );

  const tooltipContent = useCallback(
    ({ active, payload }: TooltipProps<number, string>) => {
      if (!active || !payload?.length) return null;

      const row = payload[0]?.payload as ChartRow | undefined;
      if (!row) return null;

      const platformScores = row.platform_scores ?? {};
      const platformRows = sortedPlatformTooltipRows(platformScores, platformsMeta);

      return (
        <ChartMetricTooltipPanel
          header={row.date ? formatChartTooltipDate(row.date) : undefined}
          rows={platformRows.map(({ platformId, score }) => {
            const meta = resolvePlatformMeta(platformId, platformsMeta);
            return {
              label: meta.label,
              value: formatSentimentScore(score),
              icon: (
                <PlatformLogo
                  provider={platformId}
                  label={meta.label}
                  className="size-4 rounded-sm"
                />
              ),
            };
          })}
        />
      );
    },
    [platformsMeta],
  );

  if (data.length === 0) {
    return (
      <div
        className={cn(
          "text-muted-foreground flex min-h-[120px] flex-1 items-center justify-center text-sm",
          className,
        )}
      >
        暂无数据
      </div>
    );
  }

  return (
    <div className={cn("min-h-[120px] min-w-0 w-full flex-1", className)}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
          <CartesianGrid vertical={false} stroke={GRID_STROKE} strokeDasharray="4 4" />
          <XAxis
            dataKey="dateLabel"
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={{ stroke: GRID_STROKE }}
            interval="preserveStartEnd"
            dy={4}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={AXIS_TICK}
            width={36}
            domain={[0, 100]}
            ticks={[...Y_TICKS]}
            tickFormatter={(value) => String(value)}
          />
          <Tooltip
            cursor={{ fill: HOVER_CURSOR_FILL }}
            content={tooltipContent}
            wrapperStyle={{ outline: "none", zIndex: 10 }}
          />
          <Bar dataKey="score" radius={[4, 4, 0, 0]} maxBarSize={40}>
            {data.map((row) => (
              <Cell key={row.date} fill={barColor(row.sentiment_label)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
