import {
  ChevronDown,
  ChevronsUpDown,
  ChevronUp,
  Sparkles,
} from "lucide-react";

import {
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import { MentionedBrandsCell } from "@/components/analysis/common/MentionedBrandsCell";
import {
  ColumnHelp,
  PromptTextCell,
} from "@/components/analysis/prompt/PerformanceMetricCells";
import { PerformanceTableShell } from "@/components/analysis/prompt/PerformanceTableShell";
import { performanceTableClasses } from "@/components/analysis/prompt/performanceTableLayout";
import { PlatformLogoGroup } from "@/components/brand/PlatformLogo";
import { Button } from "@/components/ui/button";
import { DotBadge, type SemanticBadgeVariant } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  CONTENT_OPPORTUNITY_COLUMNS,
  CONTENT_OPPORTUNITY_MIN_WIDTH,
  contentOpportunityColumnColStyle,
  contentOpportunityPromptCellStyle,
  type ContentOpportunityRow,
  type ContentOpportunitySortColumn,
} from "@/lib/opportunity/content";
import type { OpportunityPriority, SamplingPlatform } from "@/types";
import { cn } from "@/lib/utils";

type SortDir = "asc" | "desc";
type HeaderMode = "default" | SortDir;

export type ContentOpportunitySortState = {
  column: ContentOpportunitySortColumn;
  dir: HeaderMode;
};

export const DEFAULT_CONTENT_OPPORTUNITY_SORT: ContentOpportunitySortState = {
  column: "priority",
  dir: "default",
};

type SortState = ContentOpportunitySortState;

const PRIORITY_VARIANT: Record<OpportunityPriority, SemanticBadgeVariant> = {
  high: "error",
  medium: "warning",
  low: "success",
};

const GAP_TONE_CLASS: Record<OpportunityPriority, string> = {
  high: "text-error",
  medium: "text-warning",
  low: "text-success",
};

function cycleSort(state: SortState, column: ContentOpportunitySortColumn): SortState {
  if (state.column !== column || state.dir === "default") return { column, dir: "asc" };
  if (state.dir === "asc") return { column, dir: "desc" };
  return { column, dir: "default" };
}

type SortableHeaderProps = {
  column: ContentOpportunitySortColumn;
  label: string;
  sort: SortState;
  onSort: (column: ContentOpportunitySortColumn) => void;
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
  column?: ContentOpportunitySortColumn;
  sort?: SortState;
  onSort?: (column: ContentOpportunitySortColumn) => void;
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

function GapMetricCell({
  value,
  gapPriority,
  replySub,
}: {
  value: string;
  gapPriority: OpportunityPriority;
  replySub: string;
}) {
  return (
    <div className="flex flex-col items-start gap-0.5">
      <span className={cn("text-base font-bold tabular-nums", GAP_TONE_CLASS[gapPriority])}>
        {value}
      </span>
      <span className="text-muted-foreground text-xs tabular-nums">{replySub}</span>
    </div>
  );
}

function PriorityCell({ priority, label }: { priority: OpportunityPriority; label: string }) {
  return (
    <DotBadge variant={PRIORITY_VARIANT[priority]} className="px-2 py-0.5 text-xs">
      {label}
    </DotBadge>
  );
}

function OpportunityContentSkeletonRows({ count = 8 }: { count?: number }) {
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
            <Skeleton className="size-8 rounded-md" />
          </td>
          <td>
            <Skeleton className="h-6 w-14" />
          </td>
          <td>
            <Skeleton className="h-8 w-16" />
          </td>
          <td>
            <Skeleton className="h-8 w-16" />
          </td>
          <td className="text-center">
            <Skeleton className="mx-auto size-8 rounded-md" />
          </td>
        </tr>
      ))}
    </>
  );
}

type OpportunityContentTableProps = {
  rows: ContentOpportunityRow[];
  platformsMeta: SamplingPlatform[];
  loading?: boolean;
  className?: string;
  total: number;
  page: number;
  pageSize: number;
  sort: ContentOpportunitySortState;
  onSortChange: (sort: ContentOpportunitySortState) => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  onRowClick?: (row: ContentOpportunityRow) => void;
};

/** 内容机会表：提示词差距与竞品对比 */
export function OpportunityContentTable({
  rows,
  platformsMeta,
  loading = false,
  className,
  total,
  page,
  pageSize,
  sort,
  onSortChange,
  onPageChange,
  onPageSizeChange,
  onRowClick,
}: OpportunityContentTableProps) {
  const handlePageSizeChange = (nextPageSize: number) => {
    onPageSizeChange(nextPageSize);
    onPageChange(1);
  };

  const handleSort = (column: ContentOpportunitySortColumn) => {
    onSortChange(cycleSort(sort, column));
  };

  return (
    <PerformanceTableShell
      className={className}
      loading={loading}
      scrollMinWidth={CONTENT_OPPORTUNITY_MIN_WIDTH}
      footer={
        !loading && total > 0 ? (
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
          {CONTENT_OPPORTUNITY_COLUMNS.map((column) => (
            <col key={column.id} style={contentOpportunityColumnColStyle(column)} />
          ))}
        </colgroup>
        <thead className={performanceTableClasses.head}>
          <tr>
            <th className="overflow-hidden pl-5" style={contentOpportunityPromptCellStyle()}>
              提示词
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
                label="平台"
                description="针对该 Prompt 生成回答的 AI 大模型平台。反映了该话题在不同 AI 模型中的活跃度与覆盖情况，帮助你识别哪些 AI 渠道是当前流量的主要来源，从而进行针对性优化。"
              />
            </th>
            <th>
              <HeaderWithHelp
                label="竞争对手"
                description="在 AI 回答中被明确提及的竞争对手品牌。展示了当前在该话题下占据话语权的主导竞品，直接指明了你需要通过内容策略去对标、替代或超越的具体目标。"
              />
            </th>
            <th>
              <HeaderWithHelp
                label="品牌差距"
                description="在 AI 回答中被明确提及的竞争对手品牌。展示了当前在该话题下占据话语权的主导竞品，直接指明了你需要通过内容策略去对标、替代或超越的具体目标。"
                sortable
                column="brandGap"
                sort={sort}
                onSort={handleSort}
              />
            </th>
            <th>
              <HeaderWithHelp
                label="来源差距"
                description="在竞品链接被引用的 AI 回答中，你的网站来源未能出现的占比。该数值越高（如100%），说明在该话题下竞品的内容垄断了 AI 的参考信源，而你错失了直接的点击流量与权威背书。"
                sortable
                column="sourceGap"
                sort={sort}
                onSort={handleSort}
              />
            </th>
            <th className="text-center">操作</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <OpportunityContentSkeletonRows />
          ) : rows.length === 0 ? (
            <tr>
              <td colSpan={7} className="text-muted-foreground px-5 py-10 text-center text-sm">
                暂无内容机会
              </td>
            </tr>
          ) : (
            rows.map((row) => (
                <tr
                  key={row.id}
                  className={cn(
                    performanceTableClasses.row,
                    onRowClick && "hover:bg-muted/40 cursor-pointer",
                  )}
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
                  role={onRowClick ? "button" : undefined}
                >
                  <td className="overflow-hidden pl-5 text-foreground font-medium " style={contentOpportunityPromptCellStyle()}>
                    <PromptTextCell text={row.promptText} />
                  </td>
                  <td>
                    <PriorityCell priority={row.priority} label={row.priorityLabel} />
                  </td>
                  <td>
                    <PlatformLogoGroup
                      providers={row.platforms}
                      platforms={platformsMeta}
                      logoClassName="size-5"
                    />
                  </td>
                  <td>
                    <MentionedBrandsCell brands={row.competitors} />
                  </td>
                  <td>
                    <GapMetricCell
                      value={row.brandGap}
                      gapPriority={row.brandGapPriority}
                      replySub={row.brandGapSub}
                    />
                  </td>
                  <td>
                    <GapMetricCell
                      value={row.sourceGap}
                      gapPriority={row.sourceGapPriority}
                      replySub={row.sourceGapSub}
                    />
                  </td>
                  <td className="text-center">
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      className="text-foreground size-8 shrink-0 rounded-md disabled:opacity-100"
                      aria-label={`为「${row.promptText}」生成内容`}
                      title="生成内容（即将推出）"
                      disabled
                      onClick={(event) => event.stopPropagation()}
                    >
                      <Sparkles className="size-4" aria-hidden />
                    </Button>
                  </td>
                </tr>
            ))
          )}
        </tbody>
      </table>
    </PerformanceTableShell>
  );
}
