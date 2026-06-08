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
import {
  ColumnHelp,
  PromptTextCell,
} from "@/components/analysis/prompt/PerformanceMetricCells";
import { PerformanceTableShell } from "@/components/analysis/prompt/PerformanceTableShell";
import { performanceTableClasses } from "@/components/analysis/prompt/performanceTableLayout";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DIAGNOSIS_PROMPT_COLUMNS,
  DIAGNOSIS_PROMPT_MIN_WIDTH,
  diagnosisColumnColStyle,
  diagnosisPromptCellStyle,
  issueTypeDotClass,
  mentionRateTone,
  sortDiagnosisPromptRows,
  type DiagnosisPromptRow,
  type DiagnosisPromptSortColumn,
} from "@/lib/diagnosis";
import type { OpportunityPriority } from "@/types";
import { cn } from "@/lib/utils";

type SortState = { column: DiagnosisPromptSortColumn; dir: "asc" | "desc" | "default" };
const DEFAULT_SORT: SortState = { column: "priority", dir: "asc" };
const PRIORITY_DOT: Record<OpportunityPriority, string> = {
  high: "bg-red-500", medium: "bg-amber-500", low: "bg-muted-foreground/40",
};
const MENTION_TONE_CLASS = { high: "text-red-500", medium: "text-amber-500", low: "text-foreground" } as const;

function cycleSort(state: SortState, column: DiagnosisPromptSortColumn): SortState {
  if (state.column !== column) return { column, dir: column === "priority" ? "asc" : "desc" };
  if (state.dir === "desc") return { column, dir: "asc" };
  if (state.dir === "asc") return DEFAULT_SORT;
  return { column, dir: "desc" };
}

type DiagnosisPromptTableProps = {
  rows: DiagnosisPromptRow[];
  loading?: boolean;
};

export function DiagnosisPromptTable({ rows, loading = false }: DiagnosisPromptTableProps) {
  const [sort, setSort] = useState<SortState>(DEFAULT_SORT);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);

  const sortedRows = useMemo(() => {
    if (sort.dir === "default") return sortDiagnosisPromptRows(rows, "priority", "asc");
    return sortDiagnosisPromptRows(rows, sort.column, sort.dir as "asc" | "desc");
  }, [rows, sort]);

  const pageRows = useMemo(() => paginateRows(sortedRows, page, pageSize), [sortedRows, page, pageSize]);
  useEffect(() => setPage(1), [rows]);

  const SortableHeader = ({ column, label }: { column: DiagnosisPromptSortColumn; label: string }) => {
    const mode = sort.column === column ? sort.dir : "default";
    const icon = mode === "asc" ? <ChevronUp className="size-3" /> : mode === "desc" ? <ChevronDown className="size-3" /> : <ChevronsUpDown className="size-3" />;
    return (
      <button type="button" className={cn("inline-flex items-center gap-0.5", sort.column === column && sort.dir !== "default" ? "text-primary" : "text-muted-foreground")} onClick={() => setSort((p) => cycleSort(p, column))}>
        {label}{icon}
      </button>
    );
  };

  return (
    <PerformanceTableShell
      loading={loading}
      scrollMinWidth={DIAGNOSIS_PROMPT_MIN_WIDTH}
      footer={!loading && sortedRows.length > 0 ? (
        <TablePagination total={sortedRows.length} page={page} pageSize={pageSize} pageSizeOptions={TABLE_PAGE_SIZE_OPTIONS} onPageChange={setPage} onPageSizeChange={(n) => { setPageSize(n); setPage(1); }} />
      ) : null}
    >
      <table className={performanceTableClasses.topicTable}>
        <colgroup>
          {DIAGNOSIS_PROMPT_COLUMNS.map((column) => (
            <col key={column.id} style={diagnosisColumnColStyle(column)} />
          ))}
        </colgroup>
        <thead className={performanceTableClasses.head}>
          <tr>
            <th className="pl-5" style={diagnosisPromptCellStyle(DIAGNOSIS_PROMPT_COLUMNS[0].minWidth)}>用户正在问</th>
            <th><SortableHeader column="priority" label="行动优先级" /></th>
            <th><div className="inline-flex items-center gap-1"><SortableHeader column="mentionRate" label="AI 提及率" /><ColumnHelp label="AI 提及率" description="品牌在该提示词回复中被 AI 提及的比例。" /></div></th>
            <th>
              <div className="inline-flex items-center gap-1">
                <span>问题类型</span>
                <ColumnHelp label="问题类型" description="根据提及率与排名判断的可见度问题分类。" />
              </div>
            </th>
            <th className="text-center">操作</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            Array.from({ length: 8 }).map((_, i) => (
              <tr key={i} className={performanceTableClasses.row} aria-hidden>
                {DIAGNOSIS_PROMPT_COLUMNS.map((col) => (
                  <td key={col.id} className={col.id === "prompt" ? "pl-5" : col.id === "action" ? "text-center" : undefined}>
                    <Skeleton className={col.id === "action" ? "mx-auto size-8" : "h-4 w-16"} />
                  </td>
                ))}
              </tr>
            ))
          ) : sortedRows.length === 0 ? (
            <tr><td colSpan={5} className="text-muted-foreground px-5 py-10 text-center text-sm">暂无诊断数据</td></tr>
          ) : (
            pageRows.map((row) => (
              <tr key={row.id} className={performanceTableClasses.row}>
                <td className="overflow-hidden pl-5" style={diagnosisPromptCellStyle(DIAGNOSIS_PROMPT_COLUMNS[0].minWidth)}>
                  <PromptTextCell text={row.promptText} />
                </td>
                <td><span className={cn("mr-1.5 inline-block size-2 rounded-full", PRIORITY_DOT[row.priority])} /><span className="font-medium">{row.priorityLabel}</span></td>
                <td>
                  <div className="flex flex-col items-start gap-0.5">
                    <span className={cn("text-base font-semibold tabular-nums", MENTION_TONE_CLASS[mentionRateTone(row.mentionRateNum)])}>{row.mentionRate}</span>
                    <span className="text-muted-foreground text-xs tabular-nums">{row.mentionSub}</span>
                  </div>
                </td>
                <td><span className={cn("mr-1.5 inline-block size-2 rounded-full", issueTypeDotClass(row.issueType))} />{row.issueLabel}</td>
                <td className="text-center">
                  <Button type="button" variant="outline" size="icon" className="text-foreground size-8 rounded-md disabled:opacity-100" disabled title="生成建议（即将推出）"><Sparkles className="size-4" /></Button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </PerformanceTableShell>
  );
}
