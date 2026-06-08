import {
  ChevronDown,
  ChevronsUpDown,
  ChevronUp,
  Sparkles,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  DEFAULT_TABLE_PAGE_SIZE,
  paginateRows,
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import { BrandRankIcon } from "@/components/analysis/common/BrandRankIcon";
import {
  ColumnHelp,
  PromptTextCell,
} from "@/components/analysis/prompt/PerformanceMetricCells";
import { PerformanceTableShell } from "@/components/analysis/prompt/PerformanceTableShell";
import { performanceTableClasses } from "@/components/analysis/prompt/performanceTableLayout";
import { PlatformLogo } from "@/components/brand/PlatformLogo";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  CONTENT_OPPORTUNITY_COLUMNS,
  CONTENT_OPPORTUNITY_MIN_WIDTH,
  contentOpportunityColumnColStyle,
  contentOpportunityPromptCellStyle,
  gapTone,
  sortContentOpportunityRows,
  type ContentOpportunityRow,
  type ContentOpportunitySortColumn,
} from "@/lib/opportunity/content";
import type { OpportunityPriority, SamplingPlatform } from "@/types";
import { cn } from "@/lib/utils";

type SortDir = "asc" | "desc";
type HeaderMode = "default" | SortDir;

type SortState = {
  column: ContentOpportunitySortColumn;
  dir: HeaderMode;
};

const DEFAULT_SORT: SortState = { column: "priority", dir: "asc" };

const PRIORITY_DOT: Record<OpportunityPriority, string> = {
  high: "bg-red-500",
  medium: "bg-amber-500",
  low: "bg-muted-foreground/40",
};

const GAP_TONE_CLASS = {
  high: "text-red-500",
  medium: "text-amber-500",
  low: "text-foreground",
} as const;

function cycleSort(state: SortState, column: ContentOpportunitySortColumn): SortState {
  if (state.column !== column) {
    return { column, dir: column === "priority" ? "asc" : "desc" };
  }
  if (state.dir === "desc") return { column, dir: "asc" };
  if (state.dir === "asc") return DEFAULT_SORT;
  return { column, dir: "desc" };
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

function GapMetricCell({ value, subtext, gapNum }: { value: string; subtext: string; gapNum: number }) {
  return (
    <div className="flex flex-col items-start gap-0.5">
      <span className={cn("text-base font-bold tabular-nums", GAP_TONE_CLASS[gapTone(gapNum)])}>
        {value}
      </span>
      <span className="text-muted-foreground text-xs tabular-nums">{subtext}</span>
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
};

/** 内容机会表：提示词差距与竞品对比 */
export function OpportunityContentTable({
  rows,
  platformsMeta,
  loading = false,
  className,
}: OpportunityContentTableProps) {
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
      return sortContentOpportunityRows(rows, "priority", "asc");
    }
    return sortContentOpportunityRows(rows, sort.column, sort.dir);
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

  const handleSort = (column: ContentOpportunitySortColumn) => {
    setSort((prev) => cycleSort(prev, column));
  };

  return (
    <PerformanceTableShell
      className={className}
      loading={loading}
      scrollMinWidth={CONTENT_OPPORTUNITY_MIN_WIDTH}
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
          ) : sortedRows.length === 0 ? (
            <tr>
              <td colSpan={7} className="text-muted-foreground px-5 py-10 text-center text-sm">
                暂无内容机会
              </td>
            </tr>
          ) : (
            pageRows.map((row) => {
              const platformLabel = platformLabelById.get(row.platform) ?? row.platform;
              return (
                <tr key={row.id} className={performanceTableClasses.row}>
                  <td className="overflow-hidden pl-5 text-foreground font-medium " style={contentOpportunityPromptCellStyle()}>
                    <PromptTextCell text={row.promptText} />
                  </td>
                  <td>
                    <PriorityCell priority={row.priority} label={row.priorityLabel} />
                  </td>
                  <td>
                    <PlatformLogo provider={row.platform} label={platformLabel} className="size-7" />
                  </td>
                  <td>
                    <div className="flex items-center -space-x-1">
                      {row.competitors.length === 0 ? (
                        <span className="text-muted-foreground text-sm">—</span>
                      ) : (
                        row.competitors.slice(0, 3).map((competitor) => (
                          <BrandRankIcon key={competitor} label={competitor} size="sm" />
                        ))
                      )}
                    </div>
                  </td>
                  <td>
                    <GapMetricCell
                      value={row.brandGap}
                      subtext={row.brandGapSub}
                      gapNum={row.brandGapNum}
                    />
                  </td>
                  <td>
                    <GapMetricCell
                      value={row.sourceGap}
                      subtext={row.sourceGapSub}
                      gapNum={row.sourceGapNum}
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
                    >
                      <Sparkles className="size-4" aria-hidden />
                    </Button>
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </PerformanceTableShell>
  );
}
