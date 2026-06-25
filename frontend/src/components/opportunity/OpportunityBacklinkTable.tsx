import {
  ChevronDown,
  ChevronsUpDown,
  ChevronUp,
} from "lucide-react";

import {
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import { PerformanceTableShell } from "@/components/analysis/prompt/PerformanceTableShell";
import { performanceTableClasses } from "@/components/analysis/prompt/performanceTableLayout";
import { PlatformLogoGroup } from "@/components/brand/PlatformLogo";
import { FaviconImage } from "@/components/common/FaviconImage";
import { faviconUrlFromHost } from "@/lib/favicon";
import { DotBadge, type SemanticBadgeVariant } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  BACKLINK_OPPORTUNITY_COLUMNS,
  BACKLINK_OPPORTUNITY_MIN_WIDTH,
  backlinkOpportunityColumnColStyle,
  backlinkOpportunityDomainCellStyle,
  type BacklinkOpportunityRow,
  type BacklinkOpportunitySortColumn,
} from "@/lib/opportunity/backlink";
import type { OpportunityPriority } from "@/types";
import { cn } from "@/lib/utils";

type SortDir = "asc" | "desc";
type HeaderMode = "default" | SortDir;

export type BacklinkOpportunitySortState = {
  column: BacklinkOpportunitySortColumn;
  dir: HeaderMode;
};

export const DEFAULT_BACKLINK_OPPORTUNITY_SORT: BacklinkOpportunitySortState = {
  column: "priority",
  dir: "default",
};

type SortState = BacklinkOpportunitySortState;

const PRIORITY_VARIANT: Record<OpportunityPriority, SemanticBadgeVariant> = {
  high: "error",
  medium: "warning",
  low: "success",
};

function cycleSort(state: SortState, column: BacklinkOpportunitySortColumn): SortState {
  if (state.column !== column || state.dir === "default") return { column, dir: "asc" };
  if (state.dir === "asc") return { column, dir: "desc" };
  return { column, dir: "default" };
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

function PriorityCell({ priority, label }: { priority: OpportunityPriority; label: string }) {
  return (
    <DotBadge variant={PRIORITY_VARIANT[priority]} className="px-2 py-0.5 text-xs">
      {label}
    </DotBadge>
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
  loading?: boolean;
  fetching?: boolean;
  className?: string;
  total: number;
  page: number;
  pageSize: number;
  sort: BacklinkOpportunitySortState;
  onSortChange: (sort: BacklinkOpportunitySortState) => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  onRowClick?: (row: BacklinkOpportunityRow) => void;
};

/** 反向链接机会表：高权重引用域名与平台分布 */
export function OpportunityBacklinkTable({
  rows,
  loading = false,
  fetching = false,
  className,
  total,
  page,
  pageSize,
  sort,
  onSortChange,
  onPageChange,
  onPageSizeChange,
  onRowClick,
}: OpportunityBacklinkTableProps) {
  const handlePageSizeChange = (nextPageSize: number) => {
    onPageSizeChange(nextPageSize);
    onPageChange(1);
  };

  const handleSort = (column: BacklinkOpportunitySortColumn) => {
    onSortChange(cycleSort(sort, column));
  };

  return (
    <PerformanceTableShell
      className={className}
      loading={loading}
      fetching={fetching}
      scrollMinWidth={BACKLINK_OPPORTUNITY_MIN_WIDTH}
      footer={
        total > 0 ? (
          <TablePagination
            total={total}
            page={page}
            pageSize={pageSize}
            pageSizeOptions={TABLE_PAGE_SIZE_OPTIONS}
            onPageChange={onPageChange}
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
            <th>AI 平台</th>
            <th>
              <SortableHeader
                column="citationCount"
                label="引用次数"
                sort={sort}
                onSort={handleSort}
              />
            </th>
            <th>
              <SortableHeader
                column="promptCount"
                label="提示词数量"
                sort={sort}
                onSort={handleSort}
              />
            </th>
            <th>
              <SortableHeader
                column="chatCount"
                label="聊天次数"
                sort={sort}
                onSort={handleSort}
              />
            </th>
          </tr>
        </thead>
        <tbody>
          {loading && rows.length === 0 ? (
            <BacklinkSkeletonRows />
          ) : total === 0 ? (
            <tr>
              <td colSpan={6} className="text-muted-foreground px-5 py-10 text-center text-sm">
                暂无反向链接机会
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr
                key={row.id}
                className={cn(performanceTableClasses.row, onRowClick && "cursor-pointer")}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                onKeyDown={
                  onRowClick
                    ? (event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          onRowClick(row);
                        }
                      }
                    : undefined
                }
                tabIndex={onRowClick ? 0 : undefined}
              >
                <td className="overflow-hidden pl-5" style={backlinkOpportunityDomainCellStyle()}>
                  <div className="flex min-w-0 items-center gap-2">
                    <FaviconImage url={faviconUrlFromHost(row.domain)} size={20} className="size-5 shrink-0 rounded-sm" />
                    <span className="block min-w-0 truncate font-medium hover:text-primary hover:underline">
                      {row.domain}
                    </span>
                  </div>
                </td>
                <td>
                  <PriorityCell priority={row.priority} label={row.priorityLabel} />
                </td>
                <td>
                  <PlatformLogoGroup
                    providers={row.platforms}
                    logoClassName="size-5"
                  />
                </td>
                <td className="font-medium tabular-nums">{row.citationCount}</td>
                <td className="font-medium tabular-nums">{row.promptCount}</td>
                <td className="font-medium tabular-nums">{row.chatCount}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </PerformanceTableShell>
  );
}
