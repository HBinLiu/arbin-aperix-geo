import { ChevronDown, ChevronsUpDown, ChevronUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  DEFAULT_TABLE_PAGE_SIZE,
  paginateRows,
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import { ColumnHelp } from "@/components/analysis/prompt/PerformanceMetricCells";
import { PlatformLogo } from "@/components/brand/PlatformLogo";
import { Skeleton } from "@/components/ui/skeleton";
import { formatRate } from "@/lib/analysis/format";
import { resolvePlatformMeta } from "@/lib/analysis/shared";
import { cn } from "@/lib/utils";
import type { CitationDomainBreakdownRow, SamplingPlatform } from "@/types";

const SKELETON_ROWS = 8;
const TABLE_MIN_HEIGHT = 420;
const COUNT_DESCRIPTION = "在当前域名下被引用为来源的 AI 生成答案总数。";
const CITATION_RATE_DESCRIPTION = "在当前域名总引用量中的占比。";

type SortKey = "count" | "citation_rate";
type SortDir = "asc" | "desc";
type SortState = { key: SortKey; dir: SortDir } | null;

type CitationDomainBreakdownTableProps = {
  rows: CitationDomainBreakdownRow[];
  nameHeader: string;
  loading?: boolean;
  variant?: "text" | "platform";
  platformsMeta?: SamplingPlatform[];
  showTopicColumn?: boolean;
};

function cycleSort(prev: SortState, key: SortKey): SortState {
  if (prev?.key !== key) return { key, dir: "desc" };
  if (prev.dir === "desc") return { key, dir: "asc" };
  return null;
}

function compareRows(
  a: CitationDomainBreakdownRow,
  b: CitationDomainBreakdownRow,
  sort: SortState,
): number {
  if (!sort) {
    return b.count - a.count;
  }

  const diff =
    sort.key === "count" ? a.count - b.count : a.citation_rate - b.citation_rate;
  if (diff === 0) return a.name.localeCompare(b.name, "zh-CN");
  return sort.dir === "asc" ? diff : -diff;
}

type SortableHeaderProps = {
  label: string;
  sortKey: SortKey;
  sort: SortState;
  onSort: (key: SortKey) => void;
  help: { label: string; description: string };
};

function SortableHeader({ label, sortKey, sort, onSort, help }: SortableHeaderProps) {
  const active = sort?.key === sortKey;
  const dir = active ? sort.dir : null;

  const icon =
    dir === "asc" ? (
      <ChevronUp className="size-3 shrink-0" aria-hidden />
    ) : dir === "desc" ? (
      <ChevronDown className="size-3 shrink-0" aria-hidden />
    ) : (
      <ChevronsUpDown className="size-3 shrink-0" aria-hidden />
    );

  return (
    <span className="inline-flex items-center gap-1">
      <button
        type="button"
        className={cn(
          "inline-flex items-center gap-0.5 transition-colors",
          active ? "text-primary" : "text-muted-foreground",
        )}
        aria-label={`按${label}排序`}
        aria-sort={dir === "asc" ? "ascending" : dir === "desc" ? "descending" : "none"}
        onClick={() => onSort(sortKey)}
      >
        {label}
        {icon}
      </button>
      <ColumnHelp label={help.label} description={help.description} />
    </span>
  );
}

function SkeletonRows({ columnCount }: { columnCount: number }) {
  return (
    <>
      {Array.from({ length: SKELETON_ROWS }).map((_, rowIndex) => (
        <tr key={rowIndex} className="border-border border-t [&>td]:py-3" aria-hidden>
          {Array.from({ length: columnCount }).map((__, cellIndex) => (
            <td key={cellIndex} className={cellIndex === 0 ? "pl-5" : "px-4"}>
              <Skeleton className="h-4 w-4/5" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

export function CitationDomainBreakdownTable({
  rows,
  nameHeader,
  loading = false,
  variant = "text",
  platformsMeta = [],
  showTopicColumn = false,
}: CitationDomainBreakdownTableProps) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);
  const [sort, setSort] = useState<SortState>(null);
  const columnCount = showTopicColumn ? 4 : 3;

  const sortedRows = useMemo(
    () => [...rows].sort((a, b) => compareRows(a, b, sort)),
    [rows, sort],
  );
  const pageRows = useMemo(
    () => paginateRows(sortedRows, page, pageSize),
    [sortedRows, page, pageSize],
  );

  useEffect(() => {
    setPage(1);
  }, [sort]);

  const handlePageSizeChange = (nextPageSize: number) => {
    setPageSize(nextPageSize);
    setPage(1);
  };

  return (
    <div
      className="border-border overflow-hidden rounded-lg border bg-white"
      aria-busy={loading}
    >
      <div className="overflow-x-auto" style={{ minHeight: TABLE_MIN_HEIGHT }}>
        <table className="w-full min-w-[640px] table-fixed text-sm">
          <colgroup>
            {showTopicColumn ? (
              <>
                <col style={{ width: "40%" }} />
                <col style={{ width: "20%" }} />
                <col style={{ width: "20%" }} />
                <col style={{ width: "20%" }} />
              </>
            ) : (
              <>
                <col style={{ width: "40%" }} />
                <col style={{ width: "30%" }} />
                <col style={{ width: "30%" }} />
              </>
            )}
          </colgroup>
          <thead className="text-muted-foreground bg-muted/80 text-left">
            <tr className="[&>th]:whitespace-nowrap [&>th]:px-4 [&>th]:py-2.5 [&>th]:font-medium">
              <th className="pl-5">{nameHeader}</th>
              {showTopicColumn ? <th>主题</th> : null}
              <th>
                <SortableHeader
                  label="数量"
                  sortKey="count"
                  sort={sort}
                  onSort={(key) => setSort((prev) => cycleSort(prev, key))}
                  help={{ label: "数量", description: COUNT_DESCRIPTION }}
                />
              </th>
              <th>
                <SortableHeader
                  label="引用率"
                  sortKey="citation_rate"
                  sort={sort}
                  onSort={(key) => setSort((prev) => cycleSort(prev, key))}
                  help={{ label: "引用率", description: CITATION_RATE_DESCRIPTION }}
                />
              </th>
            </tr>
          </thead>
          <tbody className="border-border border-t">
            {loading ? (
              <SkeletonRows columnCount={columnCount} />
            ) : rows.length === 0 ? (
              <tr>
                <td
                  colSpan={columnCount}
                  className="text-muted-foreground px-4 text-center align-middle"
                  style={{ height: TABLE_MIN_HEIGHT - 40 }}
                >
                  暂无数据
                </td>
              </tr>
            ) : (
              pageRows.map((row) => {
                const platformMeta =
                  variant === "platform"
                    ? resolvePlatformMeta(row.id, platformsMeta)
                    : null;

                return (
                  <tr key={row.id} className="border-border border-t [&>td]:py-3">
                    <td className="max-w-0 pl-5">
                      {variant === "platform" && platformMeta ? (
                        <div className="flex min-w-0 items-center gap-2">
                          <PlatformLogo
                            provider={row.id}
                            label={platformMeta.label}
                            className="size-5 shrink-0 rounded-sm"
                          />
                          <span className="truncate font-medium" title={platformMeta.label}>
                            {platformMeta.label}
                          </span>
                        </div>
                      ) : (
                        <span className="line-clamp-2 font-medium" title={row.name}>
                          {row.name}
                        </span>
                      )}
                    </td>
                    {showTopicColumn ? (
                      <td className="max-w-0 px-4">
                        <span className="truncate font-medium" title={row.topic_name ?? undefined}>
                          {row.topic_name ?? "—"}
                        </span>
                      </td>
                    ) : null}
                    <td className="px-4 tabular-nums">{row.count}</td>
                    <td className="px-4 font-medium tabular-nums">
                      {formatRate(row.citation_rate)}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {!loading && rows.length > 0 ? (
        <TablePagination
          total={rows.length}
          page={page}
          pageSize={pageSize}
          pageSizeOptions={TABLE_PAGE_SIZE_OPTIONS}
          onPageChange={setPage}
          onPageSizeChange={handlePageSizeChange}
        />
      ) : null}
    </div>
  );
}
