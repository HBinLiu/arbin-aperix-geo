import {
  ChevronDown,
  ChevronsUpDown,
  ChevronUp,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  DEFAULT_TABLE_PAGE_SIZE,
  paginateRows,
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import {
  ColumnHelp,
  PromptTextCell,
} from "@/components/analysis/prompt/PerformanceMetricCells";
import { PerformanceTableShell } from "@/components/analysis/prompt/PerformanceTableShell";
import { performanceTableClasses } from "@/components/analysis/prompt/performanceTableLayout";
import { PlatformLogo } from "@/components/brand/PlatformLogo";
import { FaviconImage } from "@/components/common/FaviconImage";
import { Skeleton } from "@/components/ui/skeleton";
import {
  BACKLINK_OPPORTUNITY_COLUMNS,
  BACKLINK_OPPORTUNITY_MIN_WIDTH,
  backlinkOpportunityColumnColStyle,
  backlinkOpportunityDomainCellStyle,
  sortBacklinkOpportunityRows,
  type BacklinkOpportunityRow,
  type BacklinkOpportunitySortColumn,
} from "@/lib/opportunity/backlink";
import type { OpportunityPriority, SamplingPlatform } from "@/types";
import { cn } from "@/lib/utils";

type SortDir = "asc" | "desc";
type HeaderMode = "default" | SortDir;

type SortState = {
  column: BacklinkOpportunitySortColumn;
  dir: HeaderMode;
};

const DEFAULT_SORT: SortState = { column: "priority", dir: "asc" };

const PRIORITY_DOT: Record<OpportunityPriority, string> = {
  high: "bg-red-500",
  medium: "bg-amber-500",
  low: "bg-muted-foreground/40",
};

function cycleSort(state: SortState, column: BacklinkOpportunitySortColumn): SortState {
  if (state.column !== column) {
    return { column, dir: column === "priority" ? "asc" : "desc" };
  }
  if (state.dir === "desc") return { column, dir: "asc" };
  if (state.dir === "asc") return DEFAULT_SORT;
  return { column, dir: "desc" };
}

type SortableHeaderProps = {
  column: BacklinkOpportunitySortColumn;
  label: string;
  sort: SortState;
  onSort: (column: BacklinkOpportunitySortColumn) => void;
};

function SortableHeader({ column, label, sort, onSort }: SortableHeaderProps) {
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
      {sortIcon}
    </button>
  );
}

function HeaderWithHelp({
  label,
  description,
  sortable,
  column,
  sort,
  onSort,
}: {
  label: string;
  description: string;
  sortable?: boolean;
  column?: BacklinkOpportunitySortColumn;
  sort?: SortState;
  onSort?: (column: BacklinkOpportunitySortColumn) => void;
}) {
  return (
    <div className="inline-flex items-center gap-1">
      {sortable && column && sort && onSort ? (
        <SortableHeader column={column} label={label} sort={sort} onSort={onSort} />
      ) : (
        <span>{label}</span>
      )}
      <ColumnHelp label={label} description={description} />
    </div>
  );
}

function PriorityCell({ priority, label }: { priority: OpportunityPriority; label: string }) {
  return (
    <div className="inline-flex items-center gap-1.5">
      <span className={cn("inline-block size-2 shrink-0 rounded-full", PRIORITY_DOT[priority])} aria-hidden />
      <span className="font-medium">{label}</span>
    </div>
  );
}

function BacklinkSkeletonRows({ count = 8 }: { count?: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, rowIndex) => (
        <tr key={rowIndex} className={performanceTableClasses.row} aria-hidden>
          <td>
            <Skeleton className="h-4 w-full max-w-xs" />
          </td>
          <td>
            <Skeleton className="h-4 w-10" />
          </td>
          <td>
            <Skeleton className="h-4 w-24" />
          </td>
          <td>
            <Skeleton className="size-8 rounded-md" />
          </td>
          <td>
            <Skeleton className="h-4 w-8" />
          </td>
          <td>
            <Skeleton className="h-4 w-8" />
          </td>
        </tr>
      ))}
    </>
  );
}

type OpportunityBacklinkTableProps = {
  rows: BacklinkOpportunityRow[];
  platformsMeta: SamplingPlatform[];
  loading?: boolean;
  className?: string;
};

/** 反向链接机会表：高权重引用域名与平台分布 */
export function OpportunityBacklinkTable({
  rows,
  platformsMeta,
  loading = false,
  className,
}: OpportunityBacklinkTableProps) {
  const [sort, setSort] = useState<SortState>(DEFAULT_SORT);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);

  const platformLabelById = useMemo(() => {
    const map = new Map<string, string>();
    for (const platform of platformsMeta) {
      map.set(platform.platform, platform.label);
    }
    return map;
  }, [platformsMeta]);

  const sortedRows = useMemo(() => {
    if (sort.dir === "default") {
      return sortBacklinkOpportunityRows(rows, "priority", "asc");
    }
    return sortBacklinkOpportunityRows(rows, sort.column, sort.dir);
  }, [rows, sort]);

  const pageRows = useMemo(
    () => paginateRows(sortedRows, page, pageSize),
    [sortedRows, page, pageSize],
  );

  useEffect(() => {
    setPage(1);
  }, [rows]);

  const handlePageSizeChange = (nextPageSize: number) => {
    setPageSize(nextPageSize);
    setPage(1);
  };

  const handleSort = (column: BacklinkOpportunitySortColumn) => {
    setSort((prev) => cycleSort(prev, column));
  };

  return (
    <PerformanceTableShell
      className={className}
      loading={loading}
      scrollMinWidth={BACKLINK_OPPORTUNITY_MIN_WIDTH}
      footer={
        !loading && sortedRows.length > 0 ? (
          <TablePagination
            total={sortedRows.length}
            page={page}
            pageSize={pageSize}
            pageSizeOptions={TABLE_PAGE_SIZE_OPTIONS}
            onPageChange={setPage}
            onPageSizeChange={handlePageSizeChange}
          />
        ) : null
      }
    >
      <table className={performanceTableClasses.topicTable}>
        <colgroup>
          {BACKLINK_OPPORTUNITY_COLUMNS.map((column) => (
            <col key={column.id} style={backlinkOpportunityColumnColStyle(column)} />
          ))}
        </colgroup>
        <thead className={performanceTableClasses.head}>
          <tr>
            <th className="overflow-hidden pl-5" style={backlinkOpportunityDomainCellStyle()}>
              域名
            </th>
            <th>
              <SortableHeader
                column="priority"
                label="优先级"
                sort={sort}
                onSort={handleSort}
              />
            </th>
            <th>
              <HeaderWithHelp
                label="域名类型"
                description="根据已知品牌与竞品域名库判断该引用域名的类型。"
              />
            </th>
            <th>
              <HeaderWithHelp
                label="AI 平台"
                description="该域名在 AI 回答中被引用的平台。"
              />
            </th>
            <th>
              <HeaderWithHelp
                label="提示词数量"
                description="引用该域名且未覆盖自有域名的提示词数量。"
                sortable
                column="promptCount"
                sort={sort}
                onSort={handleSort}
              />
            </th>
            <th>
              <HeaderWithHelp
                label="聊天次数"
                description="引用该域名且未覆盖自有域名的 AI 回复次数。"
                sortable
                column="chatCount"
                sort={sort}
                onSort={handleSort}
              />
            </th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <BacklinkSkeletonRows />
          ) : sortedRows.length === 0 ? (
            <tr>
              <td colSpan={6} className="text-muted-foreground px-5 py-10 text-center text-sm">
                暂无反向链接机会
              </td>
            </tr>
          ) : (
            pageRows.map((row) => {
              const platformLabel = platformLabelById.get(row.platform) ?? row.platform;
              return (
                <tr key={row.id} className={performanceTableClasses.row}>
                  <td className="overflow-hidden pl-5" style={backlinkOpportunityDomainCellStyle()}>
                    <div className="flex min-w-0 items-center gap-2">
                      <FaviconImage domain={row.host} size={20} className="size-5 shrink-0 rounded-sm" />
                      <PromptTextCell text={row.host} />
                    </div>
                  </td>
                  <td>
                    <PriorityCell priority={row.priority} label={row.priorityLabel} />
                  </td>
                  <td>{row.domainType}</td>
                  <td>
                    <PlatformLogo provider={row.platform} label={platformLabel} className="size-7" />
                  </td>
                  <td className="font-medium tabular-nums">{row.promptCount}</td>
                  <td className="font-medium tabular-nums">{row.chatCount}</td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </PerformanceTableShell>
  );
}
