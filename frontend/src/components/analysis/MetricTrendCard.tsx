import { ArrowDown, ArrowUp, Info, Minus } from "lucide-react";

import { SimpleLineChart, CHART_COLORS } from "@/components/analysis/SimpleLineChart";
import { LabelBadge } from "@/components/common/LabelBadge";
import { Checkbox } from "@/components/ui/checkbox";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";

type MetricTrendCardProps = {
  title: string;
  value?: string;
  delta?: string | null;
  multiSeries?: { date: string; values: Record<string, number> }[];
  singleSeries?: { date: string; value: number | null }[];
  labels?: string[];
  visibleLabels?: Set<string>;
  onToggleLabel?: (label: string) => void;
  compareSeries?: { date: string; values: Record<string, number> }[];
  showCurrentPeriod?: boolean;
  onToggleCurrentPeriod?: (checked: boolean) => void;
  showPreviousPeriod?: boolean;
  onTogglePreviousPeriod?: (checked: boolean) => void;
  showCompare?: boolean;
  onToggleCompare?: (checked: boolean) => void;
  valueFormatter?: (v: number) => string;
  embedded?: boolean;
  className?: string;
};

function MetricDelta({ delta }: { delta: string | null | undefined }) {
  if (!delta) return null;

  const isUp = delta.startsWith("+");
  const isDown = delta.startsWith("-");
  const Icon = isUp ? ArrowUp : isDown ? ArrowDown : Minus;
  const variant = isUp ? "green" : isDown ? "red" : "muted";

  return (
    <LabelBadge variant={variant} className="rounded-lg px-1 py-0.5" aria-label={delta}>
      <Icon className="size-3 shrink-0" aria-hidden />
    </LabelBadge>
  );
}

export function MetricTrendCard({
  title,
  value,
  delta,
  multiSeries,
  singleSeries,
  labels = [],
  visibleLabels,
  onToggleLabel,
  compareSeries,
  showCurrentPeriod = true,
  onToggleCurrentPeriod,
  showPreviousPeriod = false,
  onTogglePreviousPeriod,
  showCompare = false,
  onToggleCompare,
  valueFormatter,
  embedded = false,
  className,
}: MetricTrendCardProps) {
  const showPeriodControls =
    onToggleCurrentPeriod || onTogglePreviousPeriod || onToggleCompare;
  const currentSeries = showCurrentPeriod ? multiSeries : undefined;
  const previousVisible = showCompare && showPreviousPeriod;

  return (
    <div
      className={cn(
        embedded ? "bg-transparent" : "border-border bg-card rounded-lg border p-4",
        className,
      )}
    >
      <div className="mb-1 flex items-center justify-between gap-3">
        <div className="min-w-0 flex flex-col gap-1">
          <div className="flex items-center gap-1.5">
            <h3 className="text-base font-semibold">{title}</h3>
            <Info className="text-muted-foreground size-3.5" aria-hidden />
          </div>
          {value ? (
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-xl font-semibold tracking-tight tabular-nums">{value}</span>
              <MetricDelta delta={delta} />
            </div>
          ) : null}
        </div>
        {showPeriodControls ? (
          <div className="flex shrink-0 flex-wrap items-center justify-end gap-3">
            {onToggleCurrentPeriod ? (
              <label className="inline-flex cursor-pointer items-center gap-1.5 text-xs">
                <Checkbox
                  checked={showCurrentPeriod}
                  onCheckedChange={(c) => onToggleCurrentPeriod(Boolean(c))}
                />
                <span className="text-muted-foreground">当前周期</span>
              </label>
            ) : null}
            {onTogglePreviousPeriod ? (
              <label
                className={cn(
                  "inline-flex cursor-pointer items-center gap-1.5 text-xs",
                  !showCompare && "cursor-not-allowed opacity-50",
                )}
              >
                <Checkbox
                  checked={showPreviousPeriod}
                  disabled={!showCompare}
                  onCheckedChange={(c) => onTogglePreviousPeriod(Boolean(c))}
                />
                <span className="text-muted-foreground">上一周期</span>
              </label>
            ) : null}
            {onToggleCompare ? (
              <label className="inline-flex cursor-pointer items-center gap-2 text-xs">
                <Switch checked={showCompare} onCheckedChange={onToggleCompare} />
                <span className="text-foreground">对比</span>
              </label>
            ) : null}
          </div>
        ) : null}
      </div>

      <div className={cn(embedded ? "mt-3" : "mt-4")}>
        <SimpleLineChart
          multiSeries={currentSeries}
          singleSeries={showCurrentPeriod ? singleSeries : undefined}
          labels={labels}
          visibleLabels={visibleLabels}
          compareSeries={previousVisible ? compareSeries : undefined}
          showCompare={previousVisible}
          valueFormatter={valueFormatter}
        />
        {labels.length > 0 && onToggleLabel ? (
          <div className="mt-2 flex flex-wrap items-center justify-center gap-x-4 gap-y-2 text-xs">
            {labels.slice(0, 5).map((lab, idx) => {
              const visible = !visibleLabels || visibleLabels.has(lab);
              return (
                <button
                  key={lab}
                  type="button"
                  onClick={() => onToggleLabel(lab)}
                  className={cn(
                    "inline-flex cursor-pointer items-center gap-1.5",
                    !visible && "opacity-40",
                  )}
                >
                  <span
                    className="inline-block size-2 shrink-0 rounded-full"
                    style={{ backgroundColor: CHART_COLORS[idx % CHART_COLORS.length] }}
                    aria-hidden
                  />
                  <span className="text-muted-foreground max-w-[6rem] truncate">{lab}</span>
                </button>
              );
            })}
          </div>
        ) : null}
      </div>
    </div>
  );
}
