import { ChevronDown, ChevronsUpDown, ChevronUp } from "lucide-react";
import { useMemo, useState } from "react";

import { buildBrandRankIcon } from "@/components/analysis/common/BrandRankIcon";
import {
  ColumnHelp,
  EmptyMetricCell,
  SentimentMetricCell,
} from "@/components/analysis/prompt/PerformanceMetricCells";
import { PerformanceTableShell } from "@/components/analysis/prompt/PerformanceTableShell";
import { performanceTableClasses } from "@/components/analysis/prompt/performanceTableLayout";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  BRAND_LEADERBOARD_COLUMNS,
  BRAND_LEADERBOARD_MIN_WIDTH,
  sortBrandLeaderboardRows,
  type BrandLeaderboardRow,
  type BrandLeaderboardSortColumn,
} from "@/lib/dashboard/rank";
import { cn } from "@/lib/utils";

type SortDir = "asc" | "desc";
type HeaderMode = "default" | SortDir;

type SortState = {
  column: BrandLeaderboardSortColumn;
  dir: HeaderMode;
};

const DEFAULT_SORT: SortState = { column: "visibility", dir: "desc" };

function cycleSort(state: SortState, column: BrandLeaderboardSortColumn): SortState {
  if (state.column !== column) {
    const col = BRAND_LEADERBOARD_COLUMNS.find((c) => c.id === column)!;
    return { column, dir: col.higherIsBetter ? "desc" : "asc" };
  }
  if (state.dir === "desc") return { column, dir: "asc" };
  if (state.dir === "asc") return DEFAULT_SORT;
  return { column, dir: "desc" };
}

type SortableHeaderProps = {
  column: BrandLeaderboardSortColumn;
  label: string;
  description?: string;
  sort: SortState;
  onSort: (column: BrandLeaderboardSortColumn) => void;
};

function SortableHeader({ column, label, description, sort, onSort }: SortableHeaderProps) {
  const isActive = sort.column === column && sort.dir !== "default";
  const mode = sort.column === column ? sort.dir : "default";

  const sortIcon =
    mode === "asc" ? (
      <ChevronUp className="size-3 shrink-0" aria-hidden />
    ) : mode === "desc" ? (
      <ChevronDown className="size-3 shrink-0" aria-hidden />
    ) : (
      <ChevronsUpDown className="size-3 shrink-0" aria-hidden />
    );

  return (
    <button
      type="button"
      className={cn(
        "inline-flex items-center gap-0.5 whitespace-nowrap transition-colors",
        isActive ? "text-primary" : "text-muted-foreground",
      )}
      aria-label={`按${label}排序`}
      aria-sort={mode === "asc" ? "ascending" : mode === "desc" ? "descending" : "none"}
      onClick={() => onSort(column)}
    >
      <span>{label}</span>
      {description ? <ColumnHelp label={label} description={description} /> : null}
      {sortIcon}
    </button>
  );
}

function BrandLeaderboardSkeletonRows({ count = 5 }: { count?: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, rowIndex) => (
        <tr key={rowIndex} className={performanceTableClasses.row} aria-hidden>
          <td className="pl-5">
            <Skeleton className="h-4 w-8" />
          </td>
          <td>
            <Skeleton className="h-4 w-28" />
          </td>
          {BRAND_LEADERBOARD_COLUMNS.map((column) => (
            <td key={column.id}>
              <Skeleton className="h-4 w-16" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

function metricCellClass(active: boolean): string {
  return cn("font-medium tabular-nums", active && "text-primary");
}

type BrandLeaderboardTableProps = {
  rows: BrandLeaderboardRow[];
  loading?: boolean;
  className?: string;
};

/** 排行榜 · 品牌全指标对比表 */
export function BrandLeaderboardTable({ rows, loading = false, className }: BrandLeaderboardTableProps) {
  const [sort, setSort] = useState<SortState>(DEFAULT_SORT);

  const sortedRows = useMemo(() => {
    if (sort.dir === "default") {
      return sortBrandLeaderboardRows(rows, "visibility", "desc");
    }
    return sortBrandLeaderboardRows(rows, sort.column, sort.dir);
  }, [rows, sort]);

  const activeColumn = sort.dir === "default" ? "visibility" : sort.column;

  return (
    <PerformanceTableShell
      className={className}
      loading={loading}
      scrollMinWidth={BRAND_LEADERBOARD_MIN_WIDTH}
    >
      <table className={performanceTableClasses.topicTable}>
        <colgroup>
          <col style={{ width: "6%" }} />
          <col style={{ width: "26%" }} />
          {BRAND_LEADERBOARD_COLUMNS.map((column) => (
            <col key={column.id} style={{ width: column.width }} />
          ))}
        </colgroup>
        <thead className={performanceTableClasses.head}>
          <tr>
            <th className="pl-5">#</th>
            <th>品牌</th>
            {BRAND_LEADERBOARD_COLUMNS.map((column) => (
              <th key={column.id}>
                <SortableHeader
                  column={column.id}
                  label={column.label}
                  description={column.description}
                  sort={sort}
                  onSort={(next) => setSort((prev) => cycleSort(prev, next))}
                />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <BrandLeaderboardSkeletonRows />
          ) : sortedRows.length === 0 ? (
            <tr>
              <td
                colSpan={BRAND_LEADERBOARD_COLUMNS.length + 2}
                className="text-muted-foreground px-5 py-10 text-center text-sm"
              >
                暂无排行榜数据
              </td>
            </tr>
          ) : (
            sortedRows.map((row, index) => (
              <tr key={row.id} className={performanceTableClasses.row}>
                <td className="text-muted-foreground pl-5 tabular-nums">#{index + 1}</td>
                <td>
                  <div className="flex items-center gap-2 whitespace-nowrap">
                    {buildBrandRankIcon(row.label)}
                    <span className="font-medium">{row.label}</span>
                    {row.isOwn ? (
                      <Badge
                        variant="orange"
                        className="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium"
                      >
                        拥有
                      </Badge>
                    ) : null}
                  </div>
                </td>
                <td className={metricCellClass(activeColumn === "visibility")}>{row.visibility}</td>
                <td className={metricCellClass(activeColumn === "shareVoice")}>
                  {row.shareVoice === "—" ? <EmptyMetricCell /> : row.shareVoice}
                </td>
                <td className={metricCellClass(activeColumn === "mention")}>{row.mention}</td>
                <td className={metricCellClass(activeColumn === "averageRank")}>
                  {row.averageRank === "—" ? <EmptyMetricCell /> : row.averageRank}
                </td>
                <td className={metricCellClass(activeColumn === "citation")}>{row.citationRate}</td>
                <td className={metricCellClass(activeColumn === "sentiment")}>
                  <SentimentMetricCell value={row.sentiment} delta={null} />
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </PerformanceTableShell>
  );
}
