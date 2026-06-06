import { ChevronDown, ChevronsUpDown, ChevronUp } from "lucide-react";
import { useMemo, useState } from "react";

import { RankTableSkeleton } from "@/components/analysis/common/MetricsSkeleton";
import { BrandRankIcon } from "@/components/analysis/common/BrandRankIcon";
import { Badge } from "@/components/ui/badge";
import { isNeutralDelta } from "@/lib/analysis/format";
import { cn } from "@/lib/utils";

export type RankRow = {
  id: string;
  label: string;
  value: string;
  /** 用于排序的原始数值（0–1 比例） */
  valueNum?: number;
  delta: string | null;
  /** 用于趋势排序的原始差值 */
  deltaSortNum?: number | null;
  isOwn?: boolean;
  icon?: React.ReactNode;
};

const DEFAULT_HEIGHT_CLASS = "max-h-[400px]";

type SortColumn = "value" | "delta";
type SortDir = "asc" | "desc";
type HeaderMode = "default" | SortDir;

/** value：降序 → 升序 → default；趋势：default → 降序 → 升序 */
type SortState = {
  value: HeaderMode;
  delta: HeaderMode;
};

/** 初始：仅 value 处于降序排序态 */
const INITIAL_SORT: SortState = { value: "desc", delta: "default" };

/** 两列均 default：数据仍按 value 降序，表头均为灰色 ⇅ */
const BOTH_DEFAULT_SORT: SortState = { value: "default", delta: "default" };

function cycleValue(mode: HeaderMode): HeaderMode {
  if (mode === "desc") return "asc";
  if (mode === "asc") return "default";
  return "desc";
}

function cycleDelta(mode: HeaderMode): HeaderMode {
  if (mode === "default") return "desc";
  if (mode === "desc") return "asc";
  return "default";
}

/** 同一时刻只有一列可处于 desc/asc，另一列强制 default */
function cycleSort(state: SortState, column: SortColumn): SortState {
  if (column === "value") {
    return { value: cycleValue(state.value), delta: "default" };
  }
  const nextDelta = cycleDelta(state.delta);
  if (nextDelta === "default") return BOTH_DEFAULT_SORT;
  return { value: "default", delta: nextDelta };
}

function resolveSort(state: SortState): { column: SortColumn; dir: SortDir } {
  if (state.delta !== "default") {
    return { column: "delta", dir: state.delta as SortDir };
  }
  if (state.value === "asc") return { column: "value", dir: "asc" };
  if (state.value === "desc") return { column: "value", dir: "desc" };
  return { column: "value", dir: "desc" };
}

function parseValueNum(value: string): number {
  const n = parseFloat(value.replace(/[^\d.-]/g, ""));
  return Number.isFinite(n) ? n : 0;
}

function parseDeltaNum(delta: string | null): number | null {
  if (!delta || isNeutralDelta(delta)) return null;
  const n = parseFloat(delta.replace(/[^\d.-]/g, ""));
  if (!Number.isFinite(n)) return null;
  return delta.startsWith("-") ? -Math.abs(n) : n;
}

function compareRankRows(a: RankRow, b: RankRow, column: SortColumn, dir: SortDir): number {
  if (column === "value") {
    const diff = (a.valueNum ?? parseValueNum(a.value)) - (b.valueNum ?? parseValueNum(b.value));
    return dir === "asc" ? diff : -diff;
  }

  const aDelta = a.deltaSortNum ?? parseDeltaNum(a.delta);
  const bDelta = b.deltaSortNum ?? parseDeltaNum(b.delta);
  if (aDelta == null && bDelta == null) return 0;
  if (aDelta == null) return 1;
  if (bDelta == null) return -1;
  return dir === "asc" ? aDelta - bDelta : bDelta - aDelta;
}

function sortRankRows(rows: RankRow[], sort: SortState): RankRow[] {
  const { column, dir } = resolveSort(sort);
  return [...rows].sort((a, b) => compareRankRows(a, b, column, dir));
}

type SortableHeaderProps = {
  column: SortColumn;
  label: string;
  sort: SortState;
  onSort: (column: SortColumn) => void;
};

function SortableHeader({ column, label, sort, onSort }: SortableHeaderProps) {
  const mode = column === "value" ? sort.value : sort.delta;
  const isHighlighted = mode !== "default";

  const ariaSort =
    mode === "asc" ? "ascending" : mode === "desc" ? "descending" : "none";

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
        isHighlighted ? "text-primary" : "text-muted-foreground",
      )}
      aria-label={`按${label}排序`}
      aria-sort={ariaSort}
      onClick={() => onSort(column)}
    >
      {label}
      {sortIcon}
    </button>
  );
}

type AnalysisRankTableProps = {
  title: string;
  valueHeader: string;
  rows: RankRow[];
  emptyMessage?: string;
  embedded?: boolean;
  showMoreFooter?: boolean;
  /** 是否展示环比趋势列，默认 true */
  showDeltaColumn?: boolean;
  /** 排名对象列标题，默认「品牌」 */
  entityHeader?: string;
  renderValue?: (row: RankRow) => React.ReactNode;
  height?: number;
  className?: string;
  loading?: boolean;
};

export function AnalysisRankTable({
  title,
  valueHeader,
  rows,
  emptyMessage = "暂无排名数据",
  embedded = false,
  showMoreFooter = false,
  showDeltaColumn = true,
  entityHeader = "品牌",
  renderValue,
  height,
  className,
  loading = false,
}: AnalysisRankTableProps) {
  const [sort, setSort] = useState<SortState>(INITIAL_SORT);
  const sortedRows = useMemo(() => sortRankRows(rows, sort), [rows, sort]);

  const heightStyle = height != null ? { height } : undefined;
  const heightClass = height != null ? "h-auto shrink-0" : DEFAULT_HEIGHT_CLASS;

  if (!loading && rows.length === 0) {
    return (
      <div
        className={cn(
          "flex flex-col",
          heightClass,
          embedded ? "bg-transparent" : "border-border bg-card rounded-lg border p-4",
          className,
        )}
        style={heightStyle}
      >
        <h3 className="text-sm font-semibold">{title}</h3>
        <div className="flex flex-1 items-center justify-center">
          <p className="text-muted-foreground text-sm">{emptyMessage}</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col overflow-hidden",
        heightClass,
        embedded ? "bg-transparent" : "border-border bg-card rounded-lg border",
        className,
      )}
      style={heightStyle}
    >
      <div className={cn("shrink-0 p-3", !embedded && "border-border border-b")}>
        <h3 className="text-sm font-semibold">{title}</h3>
      </div>
      {loading ? (
        <RankTableSkeleton showMoreFooter={showMoreFooter} />
      ) : (
        <>
          <div className="min-h-0 flex-1 overflow-x-auto overflow-y-auto">
            <table className="w-full min-w-max table-auto text-sm">
              <thead className="text-muted-foreground text-left text-xs">
                <tr className="[&>th]:whitespace-nowrap [&>th]:py-2">
                  <th className="w-10 min-w-10 px-2 pl-4 font-medium">#</th>
                  <th className="px-4 font-medium">{entityHeader}</th>
                  <th className="px-4 font-medium">
                    <SortableHeader
                      column="value"
                      label={valueHeader}
                      sort={sort}
                      onSort={(column) => setSort((prev) => cycleSort(prev, column))}
                    />
                  </th>
                  {showDeltaColumn ? (
                    <th className="px-4 font-medium">
                      <SortableHeader
                        column="delta"
                        label="趋势"
                        sort={sort}
                        onSort={(column) => setSort((prev) => cycleSort(prev, column))}
                      />
                    </th>
                  ) : null}
                </tr>
              </thead>
              <tbody>
                {sortedRows.map((row, index) => (
                  <tr key={row.id} className="border-border border-t [&>td]:whitespace-nowrap [&>td]:py-2">
                    <td className="text-foreground w-10 min-w-10 px-2 pl-4 tabular-nums">
                      #{index + 1}
                    </td>
                    <td className="px-4">
                      <div className="flex items-center gap-2 whitespace-nowrap">
                        <BrandRankIcon label={row.label} icon={row.icon} />
                        <span className="font-medium">{row.label}</span>
                        {row.isOwn ? (
                          <Badge variant="orange" className="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium">
                            拥有
                          </Badge>
                        ) : null}
                      </div>
                    </td>
                    <td className="px-4 font-medium tabular-nums">
                      {renderValue ? renderValue(row) : row.value}
                    </td>
                    {showDeltaColumn ? (
                      <td className="px-4 tabular-nums">
                        {!row.delta || isNeutralDelta(row.delta) ? (
                          <span className="font-medium tabular-nums">-</span>
                        ) : (
                          <span
                            className={cn(
                              "text-xs font-medium tabular-nums",
                              row.delta.startsWith("+")
                                ? "text-emerald-600"
                                : row.delta.startsWith("-")
                                  ? "text-red-600"
                                  : "text-muted-foreground",
                            )}
                          >
                            {row.delta}
                          </span>
                        )}
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {showMoreFooter ? (
            <div className="shrink-0 px-4 py-2">
              <button
                type="button"
                className="border-border text-foreground w-full rounded-lg border py-2 text-center text-sm font-semibold transition-colors"
              >
                更多
              </button>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
