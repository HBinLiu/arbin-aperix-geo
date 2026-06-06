import { Info } from "lucide-react";
import { useState } from "react";

import { LineChartSkeleton } from "@/components/analysis/common/MetricsSkeleton";
import { SimpleLineChart } from "@/components/analysis/common/SimpleLineChart";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Switch } from "@/components/ui/switch";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { MultiSeriesPoint } from "@/lib/analysis/chart";
import { isNeutralDelta } from "@/lib/analysis/format";
import { cn } from "@/lib/utils";

type MetricTrendCardProps = {
  title: string;
  description?: string;
  value?: string;
  delta?: string | null;
  multiSeries?: MultiSeriesPoint[];
  singleSeries?: { date: string; value: number | null }[];
  labels?: string[];
  hiddenLegendKeys?: Set<string>;
  onToggleLegendKey?: (key: string) => void;
  previousSeries?: MultiSeriesPoint[];
  showCurrentPeriod?: boolean;
  onToggleCurrentPeriod?: (checked: boolean) => void;
  showPreviousPeriod?: boolean;
  onTogglePreviousPeriod?: (checked: boolean) => void;
  /** 多品牌对比（与上一周期叠加互斥） */
  showCompare?: boolean;
  onToggleCompare?: (checked: boolean) => void;
  valueFormatter?: (v: number) => string;
  /** rate：Y 轴百分比；score：绝对值（AI 提及） */
  yAxisMode?: "rate" | "score";
  chartHeight?: number;
  embedded?: boolean;
  className?: string;
  loading?: boolean;
  /** 自定义图表（饼图 / 柱形图等），传入时替代折线图 */
  chart?: React.ReactNode;
  /** 是否展示 KPI 旁的环比 Badge，默认 true */
  showValueDelta?: boolean;
};

function MetricDelta({
  delta,
  loading,
}: {
  delta: string | null | undefined;
  loading?: boolean;
}) {
  if (loading || isNeutralDelta(delta)) {
    return (
      <Badge variant="muted" className="rounded-lg px-1.5 py-0.5 text-xs font-medium tabular-nums">
        -
      </Badge>
    );
  }
  if (!delta) return null;

  const isUp = delta.startsWith("+");
  const isDown = delta.startsWith("-");
  const variant = isUp ? "green" : isDown ? "red" : "muted";

  return (
    <Badge variant={variant} className="rounded-lg px-1.5 py-0.5 text-xs font-medium tabular-nums">
      {delta}
    </Badge>
  );
}

function MetricTitleInfo({ title, description }: { title: string; description: string }) {
  const [open, setOpen] = useState(false);

  return (
    <Tooltip open={open} onOpenChange={setOpen}>
      <TooltipTrigger asChild>
        <button
          type="button"
          className="text-muted-foreground hover:text-foreground inline-flex shrink-0 rounded-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          aria-label={`了解${title}`}
          onClick={() => setOpen((prev) => !prev)}
        >
          <Info className="size-4" aria-hidden />
        </button>
      </TooltipTrigger>
      <TooltipContent
        side="top"
        sideOffset={8}
        className="w-[250px] min-w-[250px] max-w-[250px] px-3 py-2.5 text-sm font-medium leading-relaxed text-left text-wrap"
      >
        <p className="w-full text-wrap">{description}</p>
      </TooltipContent>
    </Tooltip>
  );
}

export function MetricTrendCard({
  title,
  description,
  value,
  delta,
  multiSeries,
  singleSeries,
  labels = [],
  hiddenLegendKeys,
  onToggleLegendKey,
  previousSeries,
  showCurrentPeriod = true,
  onToggleCurrentPeriod,
  showPreviousPeriod = false,
  onTogglePreviousPeriod,
  showCompare = true,
  onToggleCompare,
  valueFormatter,
  yAxisMode = "rate",
  chartHeight,
  embedded = false,
  className,
  loading = false,
  chart,
  showValueDelta = true,
}: MetricTrendCardProps) {
  const hasPeriodControls = Boolean(
    !chart && (onToggleCurrentPeriod || onTogglePreviousPeriod || onToggleCompare),
  );
  const splitHeader = Boolean(chart);
  const fixedChart = chartHeight != null;
  const overlayPrevious = !showCompare && showPreviousPeriod;

  const displayValue = value ?? "-";

  const valueBlock = (
    <div className="flex shrink-0 items-baseline gap-2">
      <span className="text-lg font-bold tracking-tight tabular-nums">{displayValue}</span>
      {showValueDelta ? <MetricDelta delta={delta} loading={loading} /> : null}
    </div>
  );

  return (
    <div
      className={cn(
        embedded ? "bg-transparent" : "border-border bg-card rounded-lg border p-6",
        fixedChart && "flex h-full flex-col",
        className,
      )}
    >
      {splitHeader ? (
        <div className="border-border flex shrink-0 items-center justify-between gap-4 border-b pb-5">
          <div className="flex min-w-0 items-center gap-1.5">
            <h3 className="text-base font-bold">{title}</h3>
            {description ? <MetricTitleInfo title={title} description={description} /> : null}
          </div>
          {valueBlock}
        </div>
      ) : (
        <div className="mb-0.5 flex shrink-0 items-center justify-between gap-2">
          <div className="min-w-0 flex flex-col gap-2">
            <div className="flex items-center gap-1.5">
              <h3 className="text-base font-bold">{title}</h3>
              {description ? <MetricTitleInfo title={title} description={description} /> : null}
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-lg font-bold tracking-tight tabular-nums">{displayValue}</span>
              {showValueDelta ? <MetricDelta delta={delta} loading={loading} /> : null}
            </div>
          </div>
          {hasPeriodControls ? (
            <div className="flex shrink-0 flex-wrap items-center justify-end gap-5 text-sm">
              {onToggleCurrentPeriod ? (
                <label className="inline-flex cursor-pointer items-center gap-1.5">
                  <Checkbox
                    checked={showCurrentPeriod}
                    onCheckedChange={(c) => onToggleCurrentPeriod(Boolean(c))}
                  />
                  <span className="text-foreground">当前</span>
                </label>
              ) : null}
              {onTogglePreviousPeriod ? (
                <label
                  className={cn(
                    "inline-flex items-center gap-1.5",
                    showCompare ? "cursor-not-allowed opacity-50" : "cursor-pointer",
                  )}
                >
                  <Checkbox
                    checked={showPreviousPeriod}
                    disabled={showCompare}
                    onCheckedChange={(c) => onTogglePreviousPeriod(Boolean(c))}
                  />
                  <span className="text-foreground">上一周期</span>
                </label>
              ) : null}
              {onToggleCompare ? (
                <label className="inline-flex cursor-pointer items-center gap-2">
                  <Switch checked={showCompare} onCheckedChange={onToggleCompare} />
                  <span className="text-foreground">对比</span>
                </label>
              ) : null}
            </div>
          ) : null}
        </div>
      )}

      <div
        className={cn(
          "min-w-0 w-full mx-2",
          fixedChart ? "mt-2 shrink-0" : "mt-3 min-h-0 flex flex-1 flex-col",
        )}
        style={fixedChart ? { minHeight: chartHeight } : undefined}
        aria-busy={loading}
      >
        {loading ? (
          <LineChartSkeleton
            chartHeight={chartHeight}
            className={fixedChart ? "w-full" : "min-h-0 min-w-0 flex-1"}
          />
        ) : chart ? (
          chart
        ) : (
          <SimpleLineChart
            className={fixedChart ? "w-full" : "min-h-0 min-w-0 flex-1"}
            height={chartHeight}
            multiSeries={multiSeries}
            singleSeries={singleSeries}
            labels={labels}
            hiddenLegendKeys={hiddenLegendKeys}
            onToggleLegendKey={onToggleLegendKey}
            previousSeries={overlayPrevious ? previousSeries : undefined}
            overlayPrevious={overlayPrevious}
            showCurrentSeries={showCurrentPeriod}
            showPreviousSeries={showPreviousPeriod}
            valueFormatter={valueFormatter}
            yAxisMode={yAxisMode}
          />
        )}
      </div>
    </div>
  );
}
