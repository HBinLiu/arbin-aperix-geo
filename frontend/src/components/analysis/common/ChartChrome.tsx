import type { ReactNode } from "react";

import {
  buildChartTooltipRows,
  formatChartTooltipDate,
  type ChartLegendItem,
  type ChartModel,
} from "@/lib/analysis/chart";
import { cn } from "@/lib/utils";

export const CHART_GRID_STROKE = "#e4e4e4";

export function ChartLegendSwatch({ color, muted }: { color: string; muted?: boolean }) {
  return (
    <span
      className={cn(
        "inline-block size-2 shrink-0 rounded-[2px]",
        muted && "bg-muted-foreground/35",
      )}
      style={muted ? undefined : { backgroundColor: color }}
      aria-hidden
    />
  );
}

/** 折线图：可点击图例（与 hiddenLegendKeys 联动） */
export function ChartLegendContent({ items }: { items: ChartLegendItem[] }) {
  if (items.length === 0) return null;

  return (
    <div className="flex w-full min-w-0 flex-wrap items-center justify-center gap-x-3 gap-y-1.5 pt-1 text-xs leading-none">
      {items.map((item) => {
        const content = (
          <>
            <ChartLegendSwatch color={item.color} muted={!item.visible} />
            <span
              className={cn(
                "whitespace-nowrap font-medium",
                item.visible ? "text-foreground" : "text-muted-foreground",
              )}
            >
              {item.label}
            </span>
          </>
        );

        if (item.interactive && item.onToggle) {
          return (
            <button
              key={item.key}
              type="button"
              onClick={item.onToggle}
              className="inline-flex cursor-pointer items-center gap-1.5"
            >
              {content}
            </button>
          );
        }

        return (
          <span key={item.key} className="inline-flex items-center gap-1.5">
            {content}
          </span>
        );
      })}
    </div>
  );
}

/** 饼图等：静态图例列表 */
export function ChartLegendList({
  items,
  className,
}: {
  items: { label: string; color: string }[];
  className?: string;
}) {
  if (items.length === 0) return null;

  return (
    <ul
      className={cn(
        "flex flex-wrap items-center justify-center gap-x-3 gap-y-1.5 px-2 pt-1 text-xs leading-none",
        className,
      )}
    >
      {items.map((item) => (
        <li key={item.label} className="inline-flex items-center gap-1.5">
          <ChartLegendSwatch color={item.color} />
          <span className="whitespace-nowrap font-medium text-foreground">{item.label}</span>
        </li>
      ))}
    </ul>
  );
}

export type ChartMetricTooltipRow = {
  label: string;
  value: string;
  color?: string;
  icon?: ReactNode;
};

/** 与折线图 ChartTooltip 同款的数值面板（可选日期标题） */
export function ChartMetricTooltipPanel({
  rows,
  header,
}: {
  rows: ChartMetricTooltipRow[];
  header?: string;
}) {
  if (rows.length === 0) return null;

  return (
    <div className="border-border pointer-events-none min-w-[9rem] rounded-md border bg-muted-background px-2 py-2 shadow-md">
      {header ? (
        <p className="text-foreground py-1 mb-1 text-xs font-semibold">{header}</p>
      ) : null}
      <ul className="space-y-1">
        {rows.map((row) => (
          <li key={row.label} className="flex items-center justify-between gap-4 text-xs">
            <span className="inline-flex min-w-0 items-center gap-1.5">
              {row.icon ? (
                <span className="inline-flex shrink-0">{row.icon}</span>
              ) : (
                <ChartLegendSwatch color={row.color ?? "#6366f1"} />
              )}
              <span className="text-muted-foreground truncate">{row.label}</span>
            </span>
            <span className="text-foreground shrink-0 font-medium tabular-nums">{row.value}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export type ChartTooltipPayload = ReadonlyArray<{
  dataKey?: string | number;
  name?: string | number;
  value?: number;
  payload?: { date?: string };
}>;

type ChartTooltipProps = {
  active?: boolean;
  payload?: ChartTooltipPayload;
  model: ChartModel;
  valueFormatter: (v: number) => string;
  tooltipLabel?: string;
};

export function ChartTooltip({
  active,
  payload,
  model,
  valueFormatter,
  tooltipLabel,
}: ChartTooltipProps) {
  if (!active || !payload?.length) return null;

  const date = String(payload[0]?.payload?.date ?? "");
  const valuesByKey = Object.fromEntries(
    payload.map((entry) => {
      const key =
        entry.dataKey != null
          ? String(entry.dataKey)
          : entry.name != null
            ? String(entry.name)
            : "";
      return [key, Number(entry.value ?? 0)];
    }),
  );
  let rows = buildChartTooltipRows({
    valuesByKey,
    labels: model.labels,
    hiddenLegendKeys: model.hiddenLegendKeys,
    overlayPrevious: model.overlayPrevious,
    previousSeries: model.previousSeries,
    showCurrentSeries: model.showCurrentSeries,
    showPreviousSeries: model.showPreviousSeries,
    valueFormatter,
    colorLookup: model.colorLookup,
    fallbackLabel: tooltipLabel,
  });

  if (rows.length === 0) return null;

  return (
    <ChartMetricTooltipPanel
      rows={rows}
      header={date ? formatChartTooltipDate(date) : undefined}
    />
  );
}

export function ChartEmptyState({
  message = "暂无数据",
  className,
  style,
}: {
  message?: string;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <div
      className={cn("text-muted-foreground flex items-center justify-center text-sm", className)}
      style={style}
    >
      {message}
    </div>
  );
}
