import { ChevronDown, ChevronsUpDown, ChevronUp } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { RankTableSkeleton } from "@/components/analysis/common/MetricsSkeleton";
import {
  RANK_TABLE_MIN_WIDTH,
  rankTableColWidths,
} from "@/components/analysis/common/analysisRankTableLayout";
import { BrandRankLabel } from "@/components/brand/BrandRankLabel";
import { isNeutralDelta } from "@/lib/analysis/format";
import { dashboardNavToPath } from "@/lib/dashboard";
import { cn } from "@/lib/utils";

export type RankRow = {
  id: string;
  label: string;
  /** 主域名，用于 favicon；无则回退 label 首字母 */
  domain?: string | null;
  value: string;
  /** 用于排序的原始数值（0–1 比例） */
  valueNum?: number;
  delta: string | null;
  /** 用于趋势排序的原始差值 */
  deltaSortNum?: number | null;
  sentimentLabel?: string | null;
  isOwn?: boolean;
  /** 当前 FilterBar 选中的分析对象（竞品视角时为竞品行） */
  isFocus?: boolean;
  icon?: React.ReactNode;
};

const DEFAULT_HEIGHT_CLASS = "max-h-[400px]";

function rankDeltaTextClass(delta: string): string {
  if (delta.startsWith("+")) return "text-success";
  if (delta.startsWith("-")) return "text-error";
  return "text-muted-foreground";
}

function RankDeltaCell({ delta }: { delta: string | null }) {
  if (delta == null || isNeutralDelta(delta)) {
    return <span className="text-muted-foreground text-xs font-medium tabular-nums">-</span>;
  }

  return (
    <span className={cn("text-xs font-medium tabular-nums", rankDeltaTextClass(delta))}>
      {delta}
    </span>
  );
}

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

function resolveSort(state: SortState, valueDefault: SortDir = "desc"): { column: SortColumn; dir: SortDir } {
  if (state.delta !== "default") {
    return { column: "delta", dir: state.delta as SortDir };
  }
  if (state.value === "asc") return { column: "value", dir: "asc" };
  if (state.value === "desc") return { column: "value", dir: "desc" };
  return { column: "value", dir: valueDefault };
}

function parseDeltaNum(delta: string | null): number | null {
  if (!delta || isNeutralDelta(delta)) return null;
  const n = parseFloat(delta.replace(/[^\d.-]/g, ""));
  if (!Number.isFinite(n)) return null;
  return delta.startsWith("-") ? -Math.abs(n) : n;
}

function compareRankRows(a: RankRow, b: RankRow, column: SortColumn, dir: SortDir): number {
  if (column === "value") {
    const aNum = a.valueNum;
    const bNum = b.valueNum;
    if (aNum == null && bNum == null) return 0;
    if (aNum == null) return 1;
    if (bNum == null) return -1;
    const diff = aNum - bNum;
    return dir === "asc" ? diff : -diff;
  }

  const aDelta = a.deltaSortNum ?? parseDeltaNum(a.delta);
  const bDelta = b.deltaSortNum ?? parseDeltaNum(b.delta);
  if (aDelta == null && bDelta == null) return 0;
  if (aDelta == null) return 1;
  if (bDelta == null) return -1;
  return dir === "asc" ? aDelta - bDelta : bDelta - aDelta;
}

function sortRankRows(rows: RankRow[], sort: SortState, valueDefault: SortDir = "desc"): RankRow[] {
  const { column, dir } = resolveSort(sort, valueDefault);
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
  /** 点击「更多」跳转路径，默认排行榜页 */
  moreHref?: string;
  /** 是否展示环比趋势列，默认 true */
  showDeltaColumn?: boolean;
  /** 排名对象列标题，默认「品牌」 */
  entityHeader?: string;
  /** 排名对象列悬停详情卡，默认 true */
  showEntityHover?: boolean;
  renderValue?: (row: RankRow) => React.ReactNode;
  height?: number;
  className?: string;
  loading?: boolean;
  /** value 列在未显式排序时的默认方向，默认降序 */
  valueSortDefault?: SortDir;
  /** 表头初始排序态，默认 value 降序 */
  initialSort?: SortState;
};

export const AVERAGE_RANK_TABLE_SORT: SortState = { value: "asc", delta: "default" };

export function AnalysisRankTable({
  title,
  valueHeader,
  rows,
  emptyMessage = "暂无排名数据",
  embedded = false,
  showMoreFooter = false,
  moreHref = dashboardNavToPath("rank"),
  showDeltaColumn = true,
  entityHeader = "品牌",
  showEntityHover = true,
  renderValue,
  height,
  className,
  loading = false,
  valueSortDefault = "desc",
  initialSort = INITIAL_SORT,
}: AnalysisRankTableProps) {
  const [sort, setSort] = useState<SortState>(initialSort);
  const sortedRows = useMemo(
    () => sortRankRows(rows, sort, valueSortDefault),
    [rows, sort, valueSortDefault],
  );

  const heightStyle = height != null ? { height } : undefined;
  const heightClass = height != null ? "h-auto shrink-0" : DEFAULT_HEIGHT_CLASS;
  const colWidths = rankTableColWidths(showDeltaColumn);

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
        <RankTableSkeleton showMoreFooter={showMoreFooter} showDeltaColumn={showDeltaColumn} />
      ) : (
        <>
          <div className="min-h-0 flex-1 overflow-x-auto overflow-y-auto">
            <table
              className="w-full table-fixed text-sm"
              style={{ minWidth: RANK_TABLE_MIN_WIDTH }}
            >
              <colgroup>
                <col style={{ width: colWidths.index }} />
                <col style={{ width: colWidths.brand }} />
                <col style={{ width: colWidths.value }} />
                {colWidths.delta ? <col style={{ width: colWidths.delta }} /> : null}
              </colgroup>
              <thead
                className={cn(
                  "text-muted-foreground sticky top-0 z-10 text-left text-xs",
                  embedded ? "bg-white" : "bg-card",
                )}
              >
                <tr className="border-border border-b [&>th]:whitespace-nowrap [&>th]:py-2">
                  <th className="px-2 pl-4 font-medium">#</th>
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
                    <td className="text-foreground px-2 pl-4 tabular-nums">
                      #{index + 1}
                    </td>
                    <td className="min-w-0 overflow-hidden px-4 whitespace-normal">
                      <BrandRankLabel
                        label={row.label}
                        icon={row.icon}
                        domain={row.domain}
                        isOwn={row.isOwn}
                        isFocus={row.isFocus}
                        showHover={showEntityHover}
                      />
                    </td>
                    <td className="px-4 font-medium tabular-nums">
                      {renderValue ? renderValue(row) : row.value}
                    </td>
                    {showDeltaColumn ? (
                      <td className="px-4 tabular-nums">
                        <RankDeltaCell delta={row.delta} />
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {showMoreFooter ? (
            <div className="shrink-0 px-4 py-2">
              <Link
                to={moreHref}
                className="border-border text-foreground hover:bg-muted/40 block w-full rounded-lg border py-2 text-center text-sm font-semibold transition-colors"
              >
                更多
              </Link>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
