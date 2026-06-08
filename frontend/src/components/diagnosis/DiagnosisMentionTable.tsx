import {
  Check,
  ChevronDown,
  ChevronsUpDown,
  ChevronUp,
  Eye,
  Sparkles,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { BrandRankIcon } from "@/components/analysis/common/BrandRankIcon";
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
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DIAGNOSIS_MENTION_COLUMNS,
  DIAGNOSIS_MENTION_MIN_WIDTH,
  diagnosisColumnColStyle,
  diagnosisPromptCellStyle,
  issueTypeDotClass,
  mentionRateTone,
  sortDiagnosisMentionRows,
  type DiagnosisMentionRow,
  type DiagnosisMentionSortColumn,
} from "@/lib/diagnosis";
import type { OpportunityPriority, SamplingPlatform } from "@/types";
import { cn } from "@/lib/utils";

type SortDir = "asc" | "desc";
type HeaderMode = "default" | SortDir;
type SortState = { column: DiagnosisMentionSortColumn; dir: HeaderMode };
const DEFAULT_SORT: SortState = { column: "priority", dir: "asc" };

const PRIORITY_DOT: Record<OpportunityPriority, string> = {
  high: "bg-red-500",
  medium: "bg-amber-500",
  low: "bg-muted-foreground/40",
};

const MENTION_TONE_CLASS = {
  high: "text-red-500",
  medium: "text-amber-500",
  low: "text-foreground",
} as const;

function cycleSort(state: SortState, column: DiagnosisMentionSortColumn): SortState {
  if (state.column !== column) return { column, dir: column === "priority" ? "asc" : "desc" };
  if (state.dir === "desc") return { column, dir: "asc" };
  if (state.dir === "asc") return DEFAULT_SORT;
  return { column, dir: "desc" };
}

function SortableHeader({
  column,
  label,
  sort,
  onSort,
}: {
  column: DiagnosisMentionSortColumn;
  label: string;
  sort: SortState;
  onSort: (column: DiagnosisMentionSortColumn) => void;
}) {
  const isActive = sort.column === column && sort.dir !== "default";
  const mode = sort.column === column ? sort.dir : "default";
  const sortIcon =
    mode === "asc" ? <ChevronUp className="size-3 shrink-0" /> :
    mode === "desc" ? <ChevronDown className="size-3 shrink-0" /> :
    <ChevronsUpDown className="size-3 shrink-0" />;

  return (
    <button
      type="button"
      className={cn(
        "inline-flex items-center gap-0.5 whitespace-nowrap transition-colors",
        isActive ? "text-primary" : "text-muted-foreground",
      )}
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
  column?: DiagnosisMentionSortColumn;
  sort?: SortState;
  onSort?: (column: DiagnosisMentionSortColumn) => void;
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

type DiagnosisMentionTableProps = {
  rows: DiagnosisMentionRow[];
  platformsMeta: SamplingPlatform[];
  loading?: boolean;
};

export function DiagnosisMentionTable({ rows, platformsMeta, loading = false }: DiagnosisMentionTableProps) {
  const [sort, setSort] = useState<SortState>(DEFAULT_SORT);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);

  const platformLabelById = useMemo(() => {
    const map = new Map<string, string>();
    for (const platform of platformsMeta) map.set(platform.platform, platform.label);
    return map;
  }, [platformsMeta]);

  const sortedRows = useMemo(() => {
    if (sort.dir === "default") return sortDiagnosisMentionRows(rows, "priority", "asc");
    return sortDiagnosisMentionRows(rows, sort.column, sort.dir);
  }, [rows, sort]);

  const pageRows = useMemo(() => paginateRows(sortedRows, page, pageSize), [sortedRows, page, pageSize]);

  useEffect(() => setPage(1), [rows]);

  return (
    <PerformanceTableShell
      loading={loading}
      scrollMinWidth={DIAGNOSIS_MENTION_MIN_WIDTH}
      footer={
        !loading && sortedRows.length > 0 ? (
          <TablePagination
            total={sortedRows.length}
            page={page}
            pageSize={pageSize}
            pageSizeOptions={TABLE_PAGE_SIZE_OPTIONS}
            onPageChange={setPage}
            onPageSizeChange={(next) => { setPageSize(next); setPage(1); }}
          />
        ) : null
      }
    >
      <table className={performanceTableClasses.topicTable}>
        <colgroup>
          {DIAGNOSIS_MENTION_COLUMNS.map((column) => (
            <col key={column.id} style={diagnosisColumnColStyle(column)} />
          ))}
        </colgroup>
        <thead className={performanceTableClasses.head}>
          <tr>
            <th className="overflow-hidden pl-5" style={diagnosisPromptCellStyle(DIAGNOSIS_MENTION_COLUMNS[0].minWidth)}>
              用户正在问
            </th>
            <th><SortableHeader column="priority" label="行动优先级" sort={sort} onSort={(c) => setSort((p) => cycleSort(p, c))} /></th>
            <th>
              <HeaderWithHelp label="AI 提及率" description="品牌在该提示词回复中被 AI 提及的比例。" sortable column="mentionRate" sort={sort} onSort={(c) => setSort((p) => cycleSort(p, c))} />
            </th>
            <th><HeaderWithHelp label="问题类型" description="根据提及率与排名判断的可见度问题分类。" /></th>
            <th><HeaderWithHelp label="AI 平台" description="该提示词被采样的 AI 平台。" /></th>
            <th><HeaderWithHelp label="竞争对手" description="在该提示词回复中提及的竞品品牌。" /></th>
            <th className="text-center">操作</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            Array.from({ length: 8 }).map((_, i) => (
              <tr key={i} className={performanceTableClasses.row} aria-hidden>
                {DIAGNOSIS_MENTION_COLUMNS.map((col) => (
                  <td key={col.id} className={col.id === "prompt" ? "pl-5" : col.id === "action" ? "text-center" : undefined}>
                    <Skeleton className={col.id === "platform" ? "size-8 rounded-md" : col.id === "action" ? "mx-auto size-8 rounded-md" : "h-4 w-16"} />
                  </td>
                ))}
              </tr>
            ))
          ) : sortedRows.length === 0 ? (
            <tr><td colSpan={7} className="text-muted-foreground px-5 py-10 text-center text-sm">暂无诊断数据</td></tr>
          ) : (
            pageRows.map((row, index) => {
              const platformLabel = platformLabelById.get(row.platform) ?? row.platform;
              const showReviewActions = index === 0 && page === 1;
              return (
                <tr key={row.id} className={performanceTableClasses.row}>
                  <td className="overflow-hidden pl-5" style={diagnosisPromptCellStyle(DIAGNOSIS_MENTION_COLUMNS[0].minWidth)}>
                    <PromptTextCell text={row.promptText} />
                  </td>
                  <td>
                    <div className="inline-flex items-center gap-1.5">
                      <span className={cn("inline-block size-2 rounded-full", PRIORITY_DOT[row.priority])} />
                      <span className="font-medium">{row.priorityLabel}</span>
                    </div>
                  </td>
                  <td>
                    <div className="flex flex-col items-start gap-0.5">
                      <span className={cn("text-base font-semibold tabular-nums", MENTION_TONE_CLASS[mentionRateTone(row.mentionRateNum)])}>
                        {row.mentionRate}
                      </span>
                      <span className="text-muted-foreground text-xs tabular-nums">{row.mentionSub}</span>
                    </div>
                  </td>
                  <td>
                    <div className="inline-flex items-center gap-1.5">
                      <span className={cn("inline-block size-2 rounded-full", issueTypeDotClass(row.issueType))} />
                      <span>{row.issueLabel}</span>
                    </div>
                  </td>
                  <td><PlatformLogo provider={row.platform} label={platformLabel} className="size-7" /></td>
                  <td>
                    <div className="flex items-center -space-x-1">
                      {row.competitors.length === 0 ? (
                        <span className="text-muted-foreground text-sm">—</span>
                      ) : (
                        row.competitors.slice(0, 3).map((c) => <BrandRankIcon key={c} label={c} size="sm" />)
                      )}
                    </div>
                  </td>
                  <td className="text-center">
                    <div className="inline-flex items-center justify-center gap-1">
                      {showReviewActions ? (
                        <>
                          <Button type="button" variant="outline" size="icon" className="size-8 rounded-md" disabled title="查看详情（即将推出）"><Eye className="size-4" /></Button>
                          <Button type="button" variant="outline" size="icon" className="size-8 rounded-md" disabled title="标记完成（即将推出）"><Check className="size-4" /></Button>
                        </>
                      ) : (
                        <Button type="button" variant="outline" size="icon" className="text-foreground size-8 rounded-md disabled:opacity-100" disabled title="生成建议（即将推出）"><Sparkles className="size-4" /></Button>
                      )}
                    </div>
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
