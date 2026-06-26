import { useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronsUpDown, ChevronUp } from "lucide-react";

import { PaginatedTableCard } from "@/components/analysis/common/PaginatedTableCard";
import {
  DEFAULT_TABLE_PAGE_SIZE,
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import { PromptDetailResponseDialog } from "@/components/analysis/prompt/PromptDetailResponseDialog";
import { PromptTextCell, SentimentMetricCell } from "@/components/analysis/prompt/PerformanceMetricCells";
import {
  SENTIMENT_RESPONSE_TABLE_COLUMNS,
  SENTIMENT_RESPONSE_TABLE_MIN_WIDTH,
  sentimentResponseColumn,
  sentimentResponseColumnCellStyle,
  sentimentResponseColumnColStyle,
  wideTableRowClass,
} from "@/components/analysis/prompt/performanceTableLayout";
import { PlatformLogo } from "@/components/brand/PlatformLogo";
import { Skeleton } from "@/components/ui/skeleton";
import { useSentimentTabResponses } from "@/hooks/useAnalysisResponses";
import { resolvePlatformMeta } from "@/lib/analysis/shared";
import { usePlatformCatalog } from "@/hooks/usePlatformCatalog";
import { formatSentimentScore } from "@/lib/analysis/format";
import { formatSentimentDateTime, SENTIMENT_LABELS } from "@/lib/analysis/sentiment";
import type {
  AnalysisFilters,
  AnalysisResponseRow,
  LlmResponseDialogRow,
  SentimentTab,
} from "@/types";
import { cn } from "@/lib/utils";

const SENTIMENT_RESPONSE_SKELETON_ROWS = 6;

type SentimentSortDir = "asc" | "desc";
type SentimentSortState = SentimentSortDir | null;

function cycleSentimentSort(prev: SentimentSortState): SentimentSortState {
  if (prev === null) return "desc";
  if (prev === "desc") return "asc";
  return null;
}

function sentimentSortParams(sort: SentimentSortState): {
  sortBy: "created_at" | "sentiment_score" | null;
  order: "asc" | "desc";
} {
  if (!sort) {
    return { sortBy: null, order: "desc" };
  }
  return { sortBy: "sentiment_score", order: sort };
}

type SentimentSortableHeaderProps = {
  label: string;
  sort: SentimentSortState;
  onSort: () => void;
};

function SentimentSortableHeader({ label, sort, onSort }: SentimentSortableHeaderProps) {
  const icon =
    sort === "asc" ? (
      <ChevronUp className="size-3 shrink-0" aria-hidden />
    ) : sort === "desc" ? (
      <ChevronDown className="size-3 shrink-0" aria-hidden />
    ) : (
      <ChevronsUpDown className="size-3 shrink-0" aria-hidden />
    );

  return (
    <button
      type="button"
      className={cn(
        "inline-flex items-center gap-0.5 transition-colors",
        sort ? "text-primary" : "text-muted-foreground",
      )}
      aria-label={`按${label}排序`}
      aria-sort={sort === "asc" ? "ascending" : sort === "desc" ? "descending" : "none"}
      onClick={onSort}
    >
      {label}
      {icon}
    </button>
  );
}

type SentimentResponseTableProps = {
  subjectId: string;
  filters: AnalysisFilters;
  activeTab: SentimentTab;
};

function SentimentResponseSkeletonRows() {
  return (
    <>
      {Array.from({ length: SENTIMENT_RESPONSE_SKELETON_ROWS }).map((_, rowIndex) => (
        <tr key={rowIndex} className={wideTableRowClass} aria-hidden>
          {SENTIMENT_RESPONSE_TABLE_COLUMNS.map((column, columnIndex) => (
            <td
              key={column.id}
              className={cn(columnIndex === 0 ? "pl-5" : "px-4", column.id === "prompt" || column.id === "reply" ? "max-w-0 overflow-hidden" : undefined)}
              style={sentimentResponseColumnCellStyle(column)}
            >
              {column.id === "platform" ? (
                <div className="flex items-center gap-2">
                  <Skeleton className="size-6 rounded-md" />
                  <Skeleton className="h-4 w-20" />
                </div>
              ) : (
                <Skeleton className={cn("h-4", column.id === "sentiment" ? "w-12" : "w-4/5")} />
              )}
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

export function SentimentResponseTable({
  subjectId,
  filters,
  activeTab,
}: SentimentResponseTableProps) {
  const platformCatalog = usePlatformCatalog();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);
  const [sentimentSort, setSentimentSort] = useState<SentimentSortState>(null);
  const [selectedRow, setSelectedRow] = useState<LlmResponseDialogRow | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [promptText, setPromptText] = useState("");

  const { sortBy, order } = useMemo(
    () => sentimentSortParams(sentimentSort),
    [sentimentSort],
  );

  const { loading, fetching, responses, total } = useSentimentTabResponses(
    subjectId,
    filters,
    activeTab,
    { page, pageSize, sortBy, order },
  );

  const openResponseDialog = (row: AnalysisResponseRow) => {
    setSelectedRow({
      response_id: row.response_id,
      platform: row.platform_id,
      reply_preview: row.reply_preview,
    });
    setPromptText(row.prompt_text);
    setDialogOpen(true);
  };

  useEffect(() => {
    setPage(1);
  }, [activeTab, filters, sentimentSort, pageSize]);

  useEffect(() => {
    setSentimentSort(null);
    setPage(1);
  }, [activeTab]);

  const handlePageSizeChange = (nextPageSize: number) => {
    setPageSize(nextPageSize);
    setPage(1);
  };

  const emptyLabel = SENTIMENT_LABELS[activeTab];

  return (
    <PaginatedTableCard
      loading={loading}
      fetching={fetching}
      footer={
        total > 0 ? (
          <TablePagination
            total={total}
            page={page}
            pageSize={pageSize}
            pageSizeOptions={TABLE_PAGE_SIZE_OPTIONS}
            onPageChange={setPage}
            onPageSizeChange={handlePageSizeChange}
          />
        ) : null
      }
    >
        <table
          className="w-full table-fixed text-sm"
          style={{ minWidth: SENTIMENT_RESPONSE_TABLE_MIN_WIDTH }}
        >
          <colgroup>
            {SENTIMENT_RESPONSE_TABLE_COLUMNS.map((column) => (
              <col key={column.id} style={sentimentResponseColumnColStyle(column)} />
            ))}
          </colgroup>
          <thead className="text-muted-foreground bg-background/80 text-left">
            <tr className="[&>th]:whitespace-nowrap [&>th]:px-4 [&>th]:py-2.5 [&>th]:font-medium">
              <th className="pl-5">平台</th>
              <th>提示词</th>
              <th>
                <SentimentSortableHeader
                  label="情感倾向"
                  sort={sentimentSort}
                  onSort={() => {
                    setSentimentSort((prev) => cycleSentimentSort(prev));
                    setPage(1);
                  }}
                />
              </th>
              <th>回复</th>
              <th>日期</th>
            </tr>
          </thead>
          <tbody className="border-border border-t">
            {loading && responses.length === 0 ? (
              <SentimentResponseSkeletonRows />
            ) : total === 0 ? (
              <tr>
                <td colSpan={5} className="text-muted-foreground px-5 py-10 text-center text-sm">
                  暂无{emptyLabel}情感数据
                </td>
              </tr>
            ) : (
              responses.map((row) => {
                const platformMeta = resolvePlatformMeta(row.platform_id, platformCatalog);
                return (
                  <tr
                    key={row.response_id}
                    className={cn(wideTableRowClass, "cursor-pointer")}
                    onClick={() => openResponseDialog(row)}
                  >
                    <td
                      className="pl-5"
                      style={sentimentResponseColumnCellStyle(sentimentResponseColumn("platform"))}
                    >
                      <div className="flex min-w-0 items-center gap-2 whitespace-nowrap">
                        <PlatformLogo
                          provider={row.platform_id}
                          label={platformMeta.label}
                          className="size-6 shrink-0 rounded-md"
                        />
                        <span className="truncate font-medium">{platformMeta.label}</span>
                      </div>
                    </td>
                    <td
                      className="text-foreground max-w-0 overflow-hidden px-4"
                      style={sentimentResponseColumnCellStyle(sentimentResponseColumn("prompt"))}
                    >
                      <PromptTextCell text={row.prompt_text} />
                    </td>
                    <td
                      className="px-4"
                      style={sentimentResponseColumnCellStyle(sentimentResponseColumn("sentiment"))}
                    >
                      <SentimentMetricCell
                        value={formatSentimentScore(row.sentiment_score)}
                        label={row.sentiment_label}
                      />
                    </td>
                    <td
                      className="text-muted-foreground max-w-0 overflow-hidden px-4"
                      style={sentimentResponseColumnCellStyle(sentimentResponseColumn("reply"))}
                    >
                      <PromptTextCell text={row.reply_preview} />
                    </td>
                    <td
                      className="text-foreground px-4 whitespace-nowrap tabular-nums"
                      style={sentimentResponseColumnCellStyle(sentimentResponseColumn("date"))}
                    >
                      {formatSentimentDateTime(row.created_at)}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>

      <PromptDetailResponseDialog
        row={selectedRow}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        promptText={promptText}
      />
    </PaginatedTableCard>
  );
}
