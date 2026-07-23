import { Fragment, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown, ChevronsUpDown, ChevronUp } from "lucide-react";
import { Line, LineChart, ResponsiveContainer } from "recharts";

import {
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import { PromptTextCell } from "@/components/analysis/prompt/PerformanceMetricCells";
import { PerformanceTableShell } from "@/components/analysis/prompt/PerformanceTableShell";
import {
  FANOUT_TABLE_COLUMN_COUNT,
  FANOUT_TABLE_COLUMNS,
  FANOUT_TABLE_MIN_WIDTH,
  performanceTableClasses,
} from "@/components/analysis/prompt/performanceTableLayout";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { ChartMetricTooltipPanel } from "@/components/analysis/common/ChartChrome";
import { usePlatformCatalog } from "@/hooks/usePlatformCatalog";
import { buildChartColorLookup, chartColorFromLookup } from "@/lib/analysis/chart";
import { platformDistributionSegments, type FanoutPromptRow } from "@/lib/analysis/fanout";
import { formatCount } from "@/lib/analysis/format";
import { promptDetailPath } from "@/lib/analysis/nav";
import { cn } from "@/lib/utils";

type SortDir = "asc" | "desc";
export type FanoutPromptSortState = { key: "quantity"; dir: SortDir } | null;

type FanoutPromptTableProps = {
  rows: FanoutPromptRow[];
  /** 与上方趋势图同一套平台色（overview.chartLabels） */
  chartLabels?: string[];
  loading?: boolean;
  fetching?: boolean;
  total: number;
  page: number;
  pageSize: number;
  sort: FanoutPromptSortState;
  onSortChange: (sort: FanoutPromptSortState) => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
};

function PlatformDistributionBar({
  counts,
  chartLabels,
}: {
  counts: Record<string, number>;
  chartLabels: string[];
}) {
  const catalog = usePlatformCatalog();
  const colorLookup = useMemo(() => {
    const ids = chartLabels.length > 0 ? chartLabels : Object.keys(counts);
    return buildChartColorLookup(ids);
  }, [chartLabels, counts]);
  const segments = platformDistributionSegments(counts, catalog);
  if (segments.length === 0) {
    return <span className="text-muted-foreground text-xs">—</span>;
  }

  const tooltipRows = segments.map((segment) => ({
    label: segment.label,
    color: chartColorFromLookup(colorLookup, segment.id),
    value: `${Number(segment.count).toFixed(1)} (${(segment.ratio * 100).toFixed(1)}%)`,
  }));

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div
          className="bg-muted flex h-2 w-full max-w-[220px] cursor-default overflow-hidden rounded-full"
          tabIndex={0}
          role="img"
          aria-label="平台分布"
          onClick={(event) => event.stopPropagation()}
        >
          {segments.map((segment) => (
            <span
              key={segment.id}
              className="h-full"
              style={{
                width: `${Math.max(segment.ratio * 100, 2)}%`,
                backgroundColor: chartColorFromLookup(colorLookup, segment.id),
              }}
            />
          ))}
        </div>
      </TooltipTrigger>
      <TooltipContent
        side="bottom"
        sideOffset={8}
        showArrow={false}
        className="border-0 bg-transparent p-0 text-foreground shadow-none"
      >
        <div className="min-w-[14rem] [&>div]:min-w-[14rem]">
          <ChartMetricTooltipPanel header="平台分布" rows={tooltipRows} />
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

function TrendSparkline({ series }: { series: FanoutPromptRow["series"] }) {
  const data = useMemo(
    () => series.map((point) => ({ date: point.date, value: point.value ?? 0 })),
    [series],
  );
  const hasValue = data.some((point) => point.value > 0);
  if (!hasValue) {
    return <span className="text-muted-foreground text-xs">—</span>;
  }
  return (
    <div className="h-10 w-[120px]">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
          <Line
            type="monotone"
            dataKey="value"
            stroke="var(--primary)"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function cycleSort(prev: FanoutPromptSortState): FanoutPromptSortState {
  if (!prev) return { key: "quantity", dir: "desc" };
  if (prev.dir === "desc") return { key: "quantity", dir: "asc" };
  return null;
}

function FanoutExpandPanel({
  row,
  onViewMore,
}: {
  row: FanoutPromptRow;
  onViewMore: () => void;
}) {
  const previewCount = Math.min(row.top_queries?.length ?? 0, 5);

  return (
    <div className="bg-background px-5 py-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <p className="text-foreground text-xs font-semibold">前 {previewCount} 个查询扇出</p>
        <button
          type="button"
          className="text-primary text-xs font-medium hover:underline"
          onClick={(event) => {
            event.stopPropagation();
            onViewMore();
          }}
        >
          查看更多
        </button>
      </div>
      {previewCount === 0 ? (
        <p className="text-muted-foreground text-sm">暂无扇出子查询</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {(row.top_queries ?? []).slice(0, 5).map((item) => (
            <div
              key={item.query}
              className="border-border bg-muted-background flex items-start justify-between gap-3 rounded-lg border px-3 py-2.5"
            >
              <p className="text-foreground min-w-0 flex-1 text-sm leading-5">{item.query}</p>
              <span className="text-foreground font-semibold shrink-0 text-sm tabular-nums">
                {formatCount(item.frequency)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function FanoutSkeletonRows({ count = 6 }: { count?: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, rowIndex) => (
        <tr key={rowIndex} className={performanceTableClasses.row} aria-hidden>
          {FANOUT_TABLE_COLUMNS.map((column, columnIndex) => (
            <td key={column.id} className={cn(columnIndex === 0 && "pl-5")}>
              <Skeleton className={cn("h-4", columnIndex === 0 ? "w-4/5" : "w-3/5")} />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

/** 查询扇出 · 有扇出的主提示词表（可展开前 5 条子查询） */
export function FanoutPromptTable({
  rows,
  chartLabels = [],
  loading = false,
  fetching = false,
  total,
  page,
  pageSize,
  sort,
  onSortChange,
  onPageChange,
  onPageSizeChange,
}: FanoutPromptTableProps) {
  const navigate = useNavigate();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const active = sort?.key === "quantity";
  const dir = active ? sort.dir : null;

  const sortIcon =
    dir === "asc" ? (
      <ChevronUp className="size-3 shrink-0" aria-hidden />
    ) : dir === "desc" ? (
      <ChevronDown className="size-3 shrink-0" aria-hidden />
    ) : (
      <ChevronsUpDown className="size-3 shrink-0" aria-hidden />
    );

  const openDetailFanout = (promptId: string) => {
    navigate(promptDetailPath(promptId, { tab: "queryExpansion" }));
  };

  return (
    <PerformanceTableShell
      loading={loading}
      fetching={fetching}
      scrollMinWidth={FANOUT_TABLE_MIN_WIDTH}
      footer={
        total > 0 ? (
          <TablePagination
            page={page}
            pageSize={pageSize}
            total={total}
            pageSizeOptions={TABLE_PAGE_SIZE_OPTIONS}
            onPageChange={onPageChange}
            onPageSizeChange={(next) => {
              onPageSizeChange(next);
              onPageChange(1);
            }}
          />
        ) : null
      }
    >
      <table className={performanceTableClasses.topicTable}>
        <colgroup>
          {FANOUT_TABLE_COLUMNS.map((column) => (
            <col key={column.id} style={{ width: column.width }} />
          ))}
        </colgroup>
        <thead className={performanceTableClasses.head}>
          <tr>
            <th className="pl-5">提示词</th>
            <th>平台分布</th>
            <th>趋势</th>
            <th>
              <button
                type="button"
                className={cn(
                  "inline-flex items-center gap-0.5 transition-colors",
                  active ? "text-primary" : "text-muted-foreground",
                )}
                aria-label="按数量排序"
                aria-sort={dir === "asc" ? "ascending" : dir === "desc" ? "descending" : "none"}
                onClick={() => onSortChange(cycleSort(sort))}
              >
                数量
                {sortIcon}
              </button>
            </th>
          </tr>
        </thead>
        <tbody>
          {loading && rows.length === 0 ? (
            <FanoutSkeletonRows />
          ) : total === 0 ? (
            <tr>
              <td
                colSpan={FANOUT_TABLE_COLUMN_COUNT}
                className="text-muted-foreground px-5 py-10 text-center text-sm"
              >
                暂无查询扇出数据
              </td>
            </tr>
          ) : (
            rows.map((row) => {
              const expanded = expandedId === row.prompt_id;
              return (
                <Fragment key={row.prompt_id}>
                  <tr
                    className={cn(
                      performanceTableClasses.row,
                      "cursor-pointer",
                      expanded && "bg-primary/5 hover:bg-primary/5",
                    )}
                    onClick={() =>
                      setExpandedId((prev) => (prev === row.prompt_id ? null : row.prompt_id))
                    }
                  >
                    <td className="text-foreground max-w-0 overflow-hidden pl-5 font-medium">
                      <div className="flex min-w-0 items-center gap-1">
                        <PromptTextCell
                          text={row.prompt_text}
                          className="w-auto min-w-0"
                        />
                        <ChevronDown
                          className={cn(
                            "text-muted-foreground size-4 shrink-0 transition-transform",
                            expanded && "rotate-180",
                          )}
                          aria-hidden
                        />
                      </div>
                    </td>
                    <td className="text-foreground font-medium">
                      <PlatformDistributionBar
                        counts={row.platform_counts}
                        chartLabels={chartLabels}
                      />
                    </td>
                    <td className="text-foreground font-medium">
                      <TrendSparkline series={row.series} />
                    </td>
                    <td className="text-foreground font-medium tabular-nums">
                      {formatCount(row.quantity)}
                    </td>
                  </tr>
                  {expanded ? (
                    <tr className="border-border border-t">
                      <td colSpan={FANOUT_TABLE_COLUMN_COUNT} className="p-0">
                        <FanoutExpandPanel
                          row={row}
                          onViewMore={() => openDetailFanout(row.prompt_id)}
                        />
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              );
            })
          )}
        </tbody>
      </table>
    </PerformanceTableShell>
  );
}
