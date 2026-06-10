import { useNavigate } from "react-router-dom";
import { ChevronDown, ChevronsUpDown, ChevronUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  DEFAULT_TABLE_PAGE_SIZE,
  paginateRows,
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import {
  ColumnHelp,
  EmptyMetricCell,
  PromptTextCell,
  RankMetricCell,
  SentimentMetricCell,
  VisibilityMetricCell,
} from "@/components/analysis/prompt/PerformanceMetricCells";
import { PerformanceTableShell } from "@/components/analysis/prompt/PerformanceTableShell";
import { PromptPerformanceSkeletonRows } from "@/components/analysis/prompt/PerformanceTableSkeleton";
import {
  performanceTableClasses,
  PROMPT_TABLE_COLUMN_COUNT,
  PROMPT_TABLE_MIN_WIDTH,
  promptTableColumn,
  promptTableColumnCellStyle,
  promptTableColumnColStyle,
  PROMPT_TABLE_COLUMNS,
} from "@/components/analysis/prompt/performanceTableLayout";
import type { PromptPerformanceRow } from "@/lib/analysis/prompt";
import { promptDetailPath } from "@/lib/analysis/nav";
import { cn } from "@/lib/utils";

type PromptPerformanceTableProps = {
  rows: PromptPerformanceRow[];
  loading?: boolean;
  className?: string;
};

type SortKey = "visibility" | "sentiment" | "averageRank" | "citationRate";
type SortDir = "asc" | "desc";
type SortState = { key: SortKey; dir: SortDir } | null;

function sortValue(row: PromptPerformanceRow, key: SortKey): number {
  switch (key) {
    case "visibility":
      return row.visibilityNum;
    case "sentiment":
      return row.sentimentNum ?? -1;
    case "averageRank":
      return row.averageRankNum ?? Number.POSITIVE_INFINITY;
    case "citationRate":
      return row.citationNum ?? -1;
  }
}

function compareRows(a: PromptPerformanceRow, b: PromptPerformanceRow, sort: SortState): number {
  if (!sort) {
    return b.visibilityNum - a.visibilityNum;
  }

  const diff = sortValue(a, sort.key) - sortValue(b, sort.key);
  if (diff === 0) return a.promptText.localeCompare(b.promptText, "zh-CN");

  if (sort.key === "averageRank") {
    return sort.dir === "asc" ? diff : -diff;
  }
  return sort.dir === "asc" ? diff : -diff;
}

type SortableHeaderProps = {
  label: string;
  sortKey: SortKey;
  sort: SortState;
  onSort: (key: SortKey) => void;
  help?: { label: string; description: string };
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
      {help ? <ColumnHelp label={help.label} description={help.description} /> : null}
    </span>
  );
}

function cycleSort(prev: SortState, key: SortKey): SortState {
  if (prev?.key !== key) return { key, dir: "desc" };
  if (prev.dir === "desc") return { key, dir: "asc" };
  return null;
}

/** 提示词表现明细表：提示词列 minWidth 可伸缩，其余列固定 px */
export function PromptPerformanceTable({
  rows,
  loading = false,
  className,
}: PromptPerformanceTableProps) {
  const navigate = useNavigate();
  const [sort, setSort] = useState<SortState>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);

  const sortedRows = useMemo(() => {
    return [...rows].sort((a, b) => compareRows(a, b, sort));
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

  return (
    <PerformanceTableShell
      className={className}
      loading={loading}
      scrollMinWidth={PROMPT_TABLE_MIN_WIDTH}
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
      <table className={performanceTableClasses.promptTable}>
        <colgroup>
          {PROMPT_TABLE_COLUMNS.map((column) => (
            <col key={column.id} style={promptTableColumnColStyle(column)} />
          ))}
        </colgroup>
        <thead className={performanceTableClasses.head}>
          <tr>
            <th
              className="pl-5"
              style={promptTableColumnCellStyle(promptTableColumn("prompt"))}
            >
              提示词
            </th>
            <th style={promptTableColumnCellStyle(promptTableColumn("topic"))}>主题</th>
            <th style={promptTableColumnCellStyle(promptTableColumn("funnel"))}>
              <span className="inline-flex items-center gap-1">
                营销漏斗
                <ColumnHelp
                  label="营销漏斗"
                  description="提示词在营销漏斗中的阶段定位，如 BOFU（决策期）或 MOFU（考虑期）。"
                />
              </span>
            </th>
            <th style={promptTableColumnCellStyle(promptTableColumn("visibility"))}>
              <SortableHeader
                label="可见度"
                sortKey="visibility"
                sort={sort}
                onSort={(key) => setSort((prev) => cycleSort(prev, key))}
                help={{
                  label: "可见度",
                  description: "在该提示词下，至少提及一次自有品牌的 AI 回复占比。",
                }}
              />
            </th>
            <th style={promptTableColumnCellStyle(promptTableColumn("sentiment"))}>
              <SortableHeader
                label="情感倾向分数"
                sortKey="sentiment"
                sort={sort}
                onSort={(key) => setSort((prev) => cycleSort(prev, key))}
                help={{
                  label: "情感倾向分数",
                  description: "该提示词下 AI 提及自有品牌时的平均情感得分。",
                }}
              />
            </th>
            <th style={promptTableColumnCellStyle(promptTableColumn("rank"))}>
              <SortableHeader
                label="平均排名"
                sortKey="averageRank"
                sort={sort}
                onSort={(key) => setSort((prev) => cycleSort(prev, key))}
              />
            </th>
            <th style={promptTableColumnCellStyle(promptTableColumn("citation"))}>
              <SortableHeader
                label="引用率"
                sortKey="citationRate"
                sort={sort}
                onSort={(key) => setSort((prev) => cycleSort(prev, key))}
                help={{
                  label: "引用率",
                  description: "在该提示词下，提及品牌且伴随自有域名链接的回复占比。",
                }}
              />
            </th>
            <th style={promptTableColumnCellStyle(promptTableColumn("intent"))}>
              <span className="inline-flex items-center gap-1">
                意图
                <ColumnHelp
                  label="意图"
                  description="提示词的搜索意图类型，如交易型（T）或商业型（C）。"
                />
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <PromptPerformanceSkeletonRows />
          ) : sortedRows.length === 0 ? (
            <tr>
              <td colSpan={PROMPT_TABLE_COLUMN_COUNT} className="text-muted-foreground px-5 py-10 text-center text-sm">
                暂无提示词表现数据
              </td>
            </tr>
          ) : (
            pageRows.map((row) => (
              <tr
                key={row.id}
                className={cn(
                  performanceTableClasses.row,
                  "cursor-pointer transition-colors hover:bg-muted/80",
                )}
                onClick={() => navigate(promptDetailPath(row.id))}
              >
                <td
                  className="text-foreground max-w-0 overflow-hidden pl-5 font-medium"
                  style={promptTableColumnCellStyle(promptTableColumn("prompt"))}
                >
                  <PromptTextCell text={row.promptText} />
                </td>
                <td
                  className="text-foreground font-medium"
                  style={promptTableColumnCellStyle(promptTableColumn("topic"))}
                >
                  {row.topicName}
                </td>
                <td style={promptTableColumnCellStyle(promptTableColumn("funnel"))}>
                  <EmptyMetricCell />
                </td>
                <td style={promptTableColumnCellStyle(promptTableColumn("visibility"))}>
                  <VisibilityMetricCell value={row.visibility} delta={row.visibilityDelta} />
                </td>
                <td style={promptTableColumnCellStyle(promptTableColumn("sentiment"))}>
                  <SentimentMetricCell value={row.sentiment} delta={row.sentimentDelta} />
                </td>
                <td style={promptTableColumnCellStyle(promptTableColumn("rank"))}>
                  <RankMetricCell value={row.averageRank} delta={row.averageRankDelta} />
                </td>
                <td style={promptTableColumnCellStyle(promptTableColumn("citation"))}>
                  {row.citationRate}
                </td>
                <td style={promptTableColumnCellStyle(promptTableColumn("intent"))}>
                  <EmptyMetricCell />
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </PerformanceTableShell>
  );
}
