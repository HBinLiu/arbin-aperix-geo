import { useEffect, useMemo, useState } from "react";
import { Eye, EyeOff, SquarePen, Trash2 } from "lucide-react";

import { ActionTooltip } from "@/components/common/ActionTooltip";

import {
  DEFAULT_TABLE_PAGE_SIZE,
  paginateRows,
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import { PromptTextCell } from "@/components/analysis/prompt/PerformanceMetricCells";
import { PerformanceTableShell } from "@/components/analysis/prompt/PerformanceTableShell";
import { performanceTableClasses } from "@/components/analysis/prompt/performanceTableLayout";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import {
  buildPromptTableRows,
  PROMPT_TABLE_COLUMNS,
  PROMPT_TABLE_MIN_WIDTH,
  promptColumnStyle,
  promptTextCellStyle,
  type PromptTableRow,
} from "@/lib/prompt";
import type { SubjectPrompt, SubjectTopic } from "@/types";

type PromptTableProps = {
  rows: SubjectPrompt[];
  topics: SubjectTopic[];
  selectedIds: Set<string>;
  onSelectedIdsChange: (ids: Set<string>) => void;
  onEdit: (row: PromptTableRow) => void;
  onDelete: (row: PromptTableRow) => void;
  onToggleEnabled: (row: PromptTableRow) => void;
  loading?: boolean;
};

/** 提示词管理 · 数据表格 */
export function PromptTable({
  rows,
  topics,
  selectedIds,
  onSelectedIdsChange,
  onEdit,
  onDelete,
  onToggleEnabled,
  loading = false,
}: PromptTableProps) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);

  const pageRows = useMemo(() => paginateRows(rows, page, pageSize), [rows, page, pageSize]);
  const pageTableRows = useMemo(
    () => buildPromptTableRows(pageRows, topics, (page - 1) * pageSize),
    [pageRows, topics, page, pageSize],
  );

  const allSelected = pageTableRows.length > 0 && pageTableRows.every((row) => selectedIds.has(row.id));

  useEffect(() => {
    setPage(1);
  }, [rows]);

  const toggleAll = (checked: boolean) => {
    const next = new Set(selectedIds);
    for (const row of pageTableRows) {
      if (checked) next.add(row.id);
      else next.delete(row.id);
    }
    onSelectedIdsChange(next);
  };

  const toggleOne = (id: string, checked: boolean) => {
    const next = new Set(selectedIds);
    if (checked) next.add(id);
    else next.delete(id);
    onSelectedIdsChange(next);
  };

  return (
    <PerformanceTableShell
      loading={loading}
      scrollMinWidth={PROMPT_TABLE_MIN_WIDTH}
      footer={
        !loading && rows.length > 0 ? (
          <TablePagination
            total={rows.length}
            page={page}
            pageSize={pageSize}
            pageSizeOptions={TABLE_PAGE_SIZE_OPTIONS}
            onPageChange={setPage}
            onPageSizeChange={(next) => {
              setPageSize(next);
              setPage(1);
            }}
          />
        ) : null
      }
    >
      <table className={performanceTableClasses.topicTable}>
        <colgroup>
          {PROMPT_TABLE_COLUMNS.map((column) => (
            <col key={column.id} style={promptColumnStyle(column)} />
          ))}
        </colgroup>
        <thead className={performanceTableClasses.head}>
          <tr>
            <th className="pl-4">
              <Checkbox
                checked={allSelected}
                onCheckedChange={(value) => toggleAll(value === true)}
                aria-label="全选当前页"
              />
            </th>
            <th>#</th>
            <th className="pl-2" style={promptTextCellStyle(PROMPT_TABLE_COLUMNS[2].minWidth)}>
              提示词
            </th>
            <th>主题</th>
            <th>创建时间</th>
            <th className="text-center">操作</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            Array.from({ length: 8 }).map((_, index) => (
              <tr key={index} className={performanceTableClasses.row} aria-hidden>
                {PROMPT_TABLE_COLUMNS.map((column) => (
                  <td key={column.id} className={column.id === "select" ? "pl-4" : undefined}>
                    <Skeleton className="h-4 w-16" />
                  </td>
                ))}
              </tr>
            ))
          ) : rows.length === 0 ? (
            <tr>
              <td colSpan={6} className="text-muted-foreground px-5 py-10 text-center text-sm">
                暂无提示词
              </td>
            </tr>
          ) : (
            pageTableRows.map((row) => (
              <tr key={row.id} className={performanceTableClasses.row}>
                <td className="pl-4">
                  <Checkbox
                    checked={selectedIds.has(row.id)}
                    onCheckedChange={(value) => toggleOne(row.id, value === true)}
                    aria-label={`选择 ${row.text}`}
                  />
                </td>
                <td className="text-muted-foreground tabular-nums">{row.index}</td>
                <td
                  className="overflow-hidden pl-2"
                  style={promptTextCellStyle(PROMPT_TABLE_COLUMNS[2].minWidth)}
                >
                  <PromptTextCell text={row.text} />
                </td>
                <td>
                  <span className="line-clamp-2 text-sm">{row.topicName}</span>
                </td>
                <td className="text-muted-foreground text-xs tabular-nums whitespace-nowrap">
                  {row.createdAtLabel}
                </td>
                <td className="text-center">
                  <div className="inline-flex items-center justify-center gap-1">
                    <ActionTooltip label="编辑">
                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        className="size-8 rounded-md"
                        aria-label="编辑"
                        onClick={() => onEdit(row)}
                      >
                        <SquarePen className="size-4" aria-hidden />
                      </Button>
                    </ActionTooltip>
                    <ActionTooltip label={row.enabled ? "停用" : "启用"}>
                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        className="size-8 rounded-md"
                        aria-label={row.enabled ? "停用" : "启用"}
                        onClick={() => onToggleEnabled(row)}
                      >
                        {row.enabled ? (
                          <EyeOff className="size-4" aria-hidden />
                        ) : (
                          <Eye className="size-4" aria-hidden />
                        )}
                      </Button>
                    </ActionTooltip>
                    <ActionTooltip label="删除">
                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        className="size-8 rounded-md"
                        aria-label="删除"
                        onClick={() => onDelete(row)}
                      >
                        <Trash2 className="size-4" aria-hidden />
                      </Button>
                    </ActionTooltip>
                  </div>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </PerformanceTableShell>
  );
}
