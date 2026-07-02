import { useNavigate } from "react-router-dom";
import { ChevronDown, ChevronsUpDown, ChevronUp } from "lucide-react";

import {
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import {
  ColumnHelp,
  PromptTextCell,
  RankMetricCell,
  SentimentMetricCell,
  VisibilityMetricCell,
} from "@/components/analysis/prompt/PerformanceMetricCells";
import { PromptFunnelBadge } from "@/components/analysis/prompt/PromptFunnelBadge";
import { PromptIntentBadge } from "@/components/analysis/prompt/PromptIntentBadge";
import { PromptPerformanceSkeletonRows } from "@/components/analysis/prompt/PerformanceTableSkeleton";
import { PerformanceTableShell } from "@/components/analysis/prompt/PerformanceTableShell";
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
import { taxonomyOptionLabel } from "@/lib/prompt/taxonomy";
import { promptDetailPath } from "@/lib/analysis/nav";
import { usePromptTaxonomy } from "@/hooks/usePromptTaxonomy";
import { cn } from "@/lib/utils";

type SortKey = "visibility" | "sentiment" | "averageRank" | "citationRate";
type SortDir = "asc" | "desc";
export type PromptPerformanceSortState = { key: SortKey; dir: SortDir } | null;

type PromptPerformanceTableProps = {
  rows: PromptPerformanceRow[];
  loading?: boolean;
  fetching?: boolean;
  className?: string;
  total: number;
  page: number;
  pageSize: number;
  sort: PromptPerformanceSortState;
  onSortChange: (sort: PromptPerformanceSortState) => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
};

type SortableHeaderProps = {
  label: string;
  sortKey: SortKey;
  sort: PromptPerformanceSortState;
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

function cycleSort(prev: PromptPerformanceSortState, key: SortKey): PromptPerformanceSortState {
  if (prev?.key !== key) return { key, dir: "desc" };
  if (prev.dir === "desc") return { key, dir: "asc" };
  return null;
}

/** 提示词表现明细表：服务端分页与排序 */
export function PromptPerformanceTable({
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
}: PromptPerformanceTableProps) {
  const navigate = useNavigate();
  const { taxonomy } = usePromptTaxonomy();

  const handlePageSizeChange = (nextPageSize: number) => {
    onPageSizeChange(nextPageSize);
    onPageChange(1);
  };

  return (
    <PerformanceTableShell
      className={className}
      loading={loading}
      fetching={fetching}
      scrollMinWidth={PROMPT_TABLE_MIN_WIDTH}
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
                  description="根据提示词所隐含的意图深度，将其归类到营销漏斗的不同阶段，帮助您判断用户在使用 AI 搜索时所处的决策心理阶段和流量的变现潜力；认知期（TOFU）、考虑期（MOFU）、决策期（BOFU）。"
                />
              </span>
            </th>
            <th style={promptTableColumnCellStyle(promptTableColumn("decision"))}>决策场景</th>
            <th style={promptTableColumnCellStyle(promptTableColumn("visibility"))}>
              <SortableHeader
                label="可见度"
                sortKey="visibility"
                sort={sort}
                onSort={(key) => onSortChange(cycleSort(sort, key))}
                help={{
                  label: "可见度",
                  description: "提及您品牌的 AI 回复总数百分比。数值越高表示在所选渠道中的曝光度和竞争可见度越高。",
                }}
              />
            </th>
            <th style={promptTableColumnCellStyle(promptTableColumn("sentiment"))}>
              <SortableHeader
                label="情感倾向分数"
                sortKey="sentiment"
                sort={sort}
                onSort={(key) => onSortChange(cycleSort(sort, key))}
                help={{
                  label: "情感倾向分数",
                  description: "AI 在回答中提及您品牌时的情感倾向评分（正面/中立/负面），反映了 AI 模型对您品牌产品或服务的评价态度与推荐意愿，数值越高品牌推荐越正向。",
                }}
              />
            </th>
            <th style={promptTableColumnCellStyle(promptTableColumn("rank"))}>
              <SortableHeader
                label="平均排名"
                sortKey="averageRank"
                sort={sort}
                onSort={(key) => onSortChange(cycleSort(sort, key))}
                help={{
                  label: "平均排名",
                  description: "品牌在 AI 推荐列表中的平均排名。反映在 AI 系统中的优先级。排名越高（数字越小）确保立即可见度，并提高用户点击的可能性。",
                }}
              />
            </th>
            <th style={promptTableColumnCellStyle(promptTableColumn("citation"))}>
              <SortableHeader
                label="引用率"
                sortKey="citationRate"
                sort={sort}
                onSort={(key) => onSortChange(cycleSort(sort, key))}
                help={{
                  label: "引用率",
                  description: "提及品牌且引用自有域名链接的回复占比。反映内容可信度和将 AI 浏览量转化为网站流量的能力。比率越高表示被引用的内容越广泛。",
                }}
              />
            </th>
            <th style={promptTableColumnCellStyle(promptTableColumn("intent"))}>
              <span className="inline-flex items-center gap-1">
                搜索意图
                <ColumnHelp
                  label="搜索意图"
                  description="识别查询背后的搜索意图类别。通过区分教育性流量驱动因素和推动直接购买的高价值关键词，帮助调整内容策略；交易型（T）、对比型（C）、了解型（I）。"
                />
              </span>
            </th>
          </tr>
        </thead>
        <tbody>
          {loading && rows.length === 0 ? (
            <PromptPerformanceSkeletonRows />
          ) : total === 0 ? (
            <tr>
              <td colSpan={PROMPT_TABLE_COLUMN_COUNT} className="text-muted-foreground px-5 py-10 text-center text-sm">
                暂无提示词表现数据
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr
                key={row.id}
                className={cn(performanceTableClasses.row, "cursor-pointer")}
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
                <td
                  className="text-foreground font-medium" 
                  style={promptTableColumnCellStyle(promptTableColumn("funnel"))}>
                  <PromptFunnelBadge stage={row.funnelStage} />
                </td>
                <td
                  className="text-foreground font-medium"
                  style={promptTableColumnCellStyle(promptTableColumn("decision"))}
                >
                  <span className="line-clamp-2 text-sm">
                    {taxonomyOptionLabel(taxonomy.decision_types, row.decisionType)}
                  </span>
                </td>
                <td
                  className="text-foreground font-medium"
                  style={promptTableColumnCellStyle(promptTableColumn("visibility"))}>
                  <VisibilityMetricCell value={row.visibility} delta={row.visibilityDelta} />
                </td>
                <td
                  className="text-foreground font-medium"
                  style={promptTableColumnCellStyle(promptTableColumn("sentiment"))}>
                    <SentimentMetricCell
                      value={row.sentiment}
                      label={row.sentimentLabel}
                    />
                </td>
                <td
                  className="text-foreground font-medium"
                  style={promptTableColumnCellStyle(promptTableColumn("rank"))}>
                  <RankMetricCell value={row.averageRank} delta={row.averageRankDelta} />
                </td>
                <td
                  className="text-foreground font-medium"
                  style={promptTableColumnCellStyle(promptTableColumn("citation"))}>
                  {row.citationRate}
                </td>
                <td
                  className="text-foreground font-medium"
                  style={promptTableColumnCellStyle(promptTableColumn("intent"))}>
                    <PromptIntentBadge intent={row.searchIntent} />
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </PerformanceTableShell>
  );
}
