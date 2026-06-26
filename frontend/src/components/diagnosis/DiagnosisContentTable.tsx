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
  DIAGNOSIS_CONTENT_COLUMNS,
  DIAGNOSIS_CONTENT_MIN_WIDTH,
  diagnosisContentColumnColStyle,
  diagnosisContentPromptCellStyle,
  type DiagnosisContentRow,
  type DiagnosisContentSortColumn,
} from "@/lib/diagnosis/content";
import type { OpportunityPriority } from "@/types";
import { cn } from "@/lib/utils";

type SortDir = "asc" | "desc";
type HeaderMode = "default" | SortDir;

export type DiagnosisContentSortState = {
  column: DiagnosisContentSortColumn;
  dir: HeaderMode;
};

export const DEFAULT_DIAGNOSIS_CONTENT_SORT: DiagnosisContentSortState = {
  column: "priority",
  dir: "default",
};

type SortState = DiagnosisContentSortState;

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

function cycleSort(state: SortState, column: DiagnosisContentSortColumn): SortState {
  if (state.column !== column || state.dir === "default") return { column, dir: "asc" };
  if (state.dir === "asc") return { column, dir: "desc" };
  return { column, dir: "default" };
}

type SortableHeaderProps = {
  column: DiagnosisContentSortColumn;
  label: string;
  sort: SortState;
  onSort: (column: DiagnosisContentSortColumn) => void;
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
  column?: DiagnosisContentSortColumn;
  sort?: SortState;
  onSort?: (column: DiagnosisContentSortColumn) => void;
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

const MENTION_TONE_CLASS = {
  high: "text-error",
  medium: "text-warning",
  low: "text-success",
} as const;

function MentionRateCell({
  value,
  mentionPriority,
  replySub,
}: {
  value: string;
  mentionPriority: OpportunityPriority;
  replySub: string;
}) {
  return (
    <div className="flex flex-col items-start gap-0.5">
      <span className={cn("text-base font-bold tabular-nums", MENTION_TONE_CLASS[mentionPriority])}>
        {value}
      </span>
      <span className="text-muted-foreground text-xs tabular-nums">{replySub}</span>
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

function DiagnosisContentSkeletonRows({ count = 8 }: { count?: number }) {
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

type DiagnosisContentTableProps = {
  rows: DiagnosisContentRow[];
  loading?: boolean;
  fetching?: boolean;
  className?: string;
  total: number;
  page: number;
  pageSize: number;
  sort: DiagnosisContentSortState;
  onSortChange: (sort: DiagnosisContentSortState) => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  onRowClick?: (row: DiagnosisContentRow) => void;
};

/** 诊断中心内容表：提示词差距与竞品对比 */
export function DiagnosisContentTable({
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
}: DiagnosisContentTableProps) {
  const handlePageSizeChange = (nextPageSize: number) => {
    onPageSizeChange(nextPageSize);
    onPageChange(1);
  };

  const handleSort = (column: DiagnosisContentSortColumn) => {
    onSortChange(cycleSort(sort, column));
  };

  return (
    <PerformanceTableShell
      className={className}
      loading={loading}
      fetching={fetching}
      scrollMinWidth={DIAGNOSIS_CONTENT_MIN_WIDTH}
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
          {DIAGNOSIS_CONTENT_COLUMNS.map((column) => (
            <col key={column.id} style={diagnosisContentColumnColStyle(column)} />
          ))}
        </colgroup>
        <thead className={performanceTableClasses.head}>
          <tr>
            <th className="overflow-hidden pl-5" style={diagnosisContentPromptCellStyle()}>
              提示词
            </th>
            <th>
              <HeaderWithHelp
                label="总优先级"
                description="综合 AI 提及率、品牌差距、来源差距三个维度的行动优先级。"
                sortable
                column="priority"
                sort={sort}
                onSort={handleSort}
              />
            </th>
            <th>
              <HeaderWithHelp
                label="平台"
                description="此话题在不同 AI 模型中的活跃度与覆盖情况，帮助你识别哪些 AI 渠道是当前流量的主要来源，从而进行针对性优化。"
              />
            </th>
            <th>
              <HeaderWithHelp
                label="竞争对手"
                description="在此话题下占据话语权的主导竞品，直接指明了你需要通过内容策略去对标、替代或超越的具体目标。"
              />
            </th>
            <th>
              <HeaderWithHelp
                label="AI 提及率"
                description="AI 回复正文中品牌提及的频率；数值颜色由 AI 提及率行动优先级决定：完全未提及为高，提及不足或排名靠后为中，表现良好为低。"
                sortable
                column="mentionRate"
                sort={sort}
                onSort={handleSort}
              />
            </th>
            <th>
              <HeaderWithHelp
                label="品牌差距"
                description="在竞品已出现的 AI 回答中，你的品牌未能出现的占比；数值颜色由品牌差距行动优先级决定（≥80% 高，≥50% 中，<50% 低）。"
                sortable
                column="brandGap"
                sort={sort}
                onSort={handleSort}
              />
            </th>
            <th>
              <HeaderWithHelp
                label="来源差距"
                description="在竞品链接被引用的 AI 回答中，你的网站来源未能出现的占比；数值颜色由引用差距行动优先级决定（≥80% 高，≥50% 中，<50% 低）。"
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
          {loading && rows.length === 0 ? (
            <DiagnosisContentSkeletonRows />
          ) : rows.length === 0 ? (
            <tr>
              <td colSpan={8} className="text-muted-foreground px-5 py-10 text-center text-sm">
                暂无诊断数据
              </td>
            </tr>
          ) : (
            rows.map((row) => (
                <tr
                  key={row.id}
                  className={cn(
                    performanceTableClasses.row,
                    onRowClick && "cursor-pointer",
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
                  <td className="overflow-hidden pl-5 text-foreground font-medium " style={diagnosisContentPromptCellStyle()}>
                    <PromptTextCell text={row.promptText} />
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
                  <td>
                    <MentionedBrandsCell brands={row.competitors} />
                  </td>
                  <td>
                    <MentionRateCell
                      value={row.mentionRate}
                      mentionPriority={row.mentionPriority}
                      replySub={row.mentionSub}
                    />
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
