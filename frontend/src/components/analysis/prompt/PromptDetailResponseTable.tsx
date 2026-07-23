import { useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronsUpDown, ChevronUp } from "lucide-react";

import {
  DEFAULT_TABLE_PAGE_SIZE,
  paginateRows,
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import { TableScrollOverlay } from "@/components/analysis/common/TableScrollOverlay";
import { MentionedBrandsCell } from "@/components/analysis/common/MentionedBrandsCell";
import {
  ColumnHelp,
  PromptTextCell,
} from "@/components/analysis/prompt/PerformanceMetricCells";
import { PromptDetailResponseDialog } from "@/components/analysis/prompt/PromptDetailResponseDialog";
import { PlatformLogo } from "@/components/brand/PlatformLogo";
import { DotBadge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatRank } from "@/lib/analysis/format";
import {
  PROMPT_DETAIL_RESPONSE_TABS,
  promptDetailResponsesForTab,
  queryExpansionEmptyMessage,
  type PromptDetailResponseTab,
} from "@/lib/analysis/promptDetail";
import { formatSentimentDateTime } from "@/lib/analysis/sentiment";
import { resolvePlatformMeta } from "@/lib/analysis/shared";
import { usePlatformCatalog } from "@/hooks/usePlatformCatalog";
import type { PromptDetailData, PromptDetailResponseRow } from "@/types";
import {
  performanceTableClasses,
  PROMPT_DETAIL_RESPONSE_TABLE_COLUMNS,
  PROMPT_DETAIL_RESPONSE_TABLE_MIN_WIDTH,
  promptDetailResponseColumnCellStyle,
  promptDetailResponseColumnColStyle,
  wideTableRowClass,
} from "@/components/analysis/prompt/performanceTableLayout";
import { cn } from "@/lib/utils";

const SKELETON_ROWS = 6;
const DATE_COLUMN = PROMPT_DETAIL_RESPONSE_TABLE_COLUMNS.find((column) => column.id === "date")!;
const DATE_CELL_STYLE = promptDetailResponseColumnCellStyle(DATE_COLUMN);

type RankSortState = "asc" | "desc" | null;

function cycleRankSort(prev: RankSortState): RankSortState {
  if (prev === null) return "desc";
  if (prev === "desc") return "asc";
  return null;
}

function rankSortValue(rank: number | null | undefined): number {
  return rank ?? Number.POSITIVE_INFINITY;
}

function compareByRank(
  a: PromptDetailResponseRow,
  b: PromptDetailResponseRow,
  sort: RankSortState,
): number {
  if (!sort) return 0;

  const diff = rankSortValue(a.rank) - rankSortValue(b.rank);
  if (diff === 0) {
    return b.created_at.localeCompare(a.created_at);
  }
  return sort === "asc" ? diff : -diff;
}

type RankSortableHeaderProps = {
  label: string;
  sort: RankSortState;
  onSort: () => void;
  help: { label: string; description: string };
};

function RankSortableHeader({ label, sort, onSort, help }: RankSortableHeaderProps) {
  const icon =
    sort === "asc" ? (
      <ChevronUp className="size-3 shrink-0" aria-hidden />
    ) : sort === "desc" ? (
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
          sort ? "text-primary" : "text-muted-foreground",
        )}
        aria-label={`按${label}排序`}
        aria-sort={sort === "asc" ? "ascending" : sort === "desc" ? "descending" : "none"}
        onClick={onSort}
      >
        {label}
        {icon}
      </button>
      <ColumnHelp label={help.label} description={help.description} />
    </span>
  );
}

type PromptDetailResponseTableProps = {
  activeTab: PromptDetailResponseTab;
  data: PromptDetailData | null;
  chatResponses?: PromptDetailResponseRow[];
  chatTotal?: number;
  chatPage?: number;
  chatPageSize?: number;
  onChatPageChange?: (page: number) => void;
  onChatPageSizeChange?: (pageSize: number) => void;
  rankSort?: RankSortState;
  onRankSortChange?: (sort: RankSortState) => void;
  promptText: string;
  loading?: boolean;
  fetching?: boolean;
};

function MentionStatusCell({ mentioned }: { mentioned: boolean }) {
  return (
    <DotBadge variant={mentioned ? "success" : "error"} className="px-1.5 py-0.5 font-semibold">
      {mentioned ? "是" : "否"}
    </DotBadge>
  );
}

function SkeletonRows() {
  return (
    <>
      {Array.from({ length: SKELETON_ROWS }).map((_, index) => (
        <tr key={index} className={wideTableRowClass} aria-hidden>
          <td className="pl-5">
            <div className="flex items-center gap-2 whitespace-nowrap">
              <Skeleton className="size-6 rounded-md" />
              <Skeleton className="h-4 w-24" />
            </div>
          </td>
          <td className="max-w-0">
            <Skeleton className="h-4 w-4/5" />
          </td>
          <td>
            <Skeleton className="h-6 w-16 rounded-full" />
          </td>
          <td>
            <Skeleton className="h-5 w-12 rounded-full" />
          </td>
          <td>
            <Skeleton className="h-4 w-10" />
          </td>
          <td style={DATE_CELL_STYLE}>
            <Skeleton className="h-4 w-36" />
          </td>
        </tr>
      ))}
    </>
  );
}

function ResponseRow({
  row,
  onSelect,
}: {
  row: PromptDetailResponseRow;
  onSelect: (row: PromptDetailResponseRow) => void;
}) {
  const platformCatalog = usePlatformCatalog();
  const platformMeta = resolvePlatformMeta(row.platform, platformCatalog);

  return (
    <tr
      className={cn(wideTableRowClass, "cursor-pointer")}
      onClick={() => onSelect(row)}
    >
      <td className="pl-5">
        <div className="flex items-center gap-2 whitespace-nowrap">
          <PlatformLogo
            provider={row.platform}
            label={platformMeta.label}
            className="size-6 rounded-md"
          />
          <span className="font-medium">{platformMeta.label}</span>
        </div>
      </td>
      <td className="text-muted-foreground max-w-0 pl-4 pr-8">
        <PromptTextCell text={row.reply_preview} />
      </td>
      <td className="px-4 font-semibold tabular-nums">
        <MentionedBrandsCell brands={row.mentioned_brands} />
      </td>
      <td className="px-4 font-semibold tabular-nums">
        <MentionStatusCell mentioned={row.mentioned} />
      </td>
      <td className="px-4 font-semibold tabular-nums">
        {formatRank(row.rank)}
      </td>
      <td className="text-foreground px-4 whitespace-nowrap tabular-nums" style={DATE_CELL_STYLE}>
        {formatSentimentDateTime(row.created_at)}
      </td>
    </tr>
  );
}

function QueryExpansionRow({
  row,
  onSelect,
}: {
  row: PromptDetailResponseRow;
  onSelect: (row: PromptDetailResponseRow) => void;
}) {
  const platformCatalog = usePlatformCatalog();
  const platformMeta = resolvePlatformMeta(row.platform, platformCatalog);
  const queries = row.search_queries ?? [];
  const depthLabel =
    queries.length > 0 ? `扇出 ${queries.length} 条` : queryExpansionEmptyMessage(row);

  return (
    <tr
      className={cn(wideTableRowClass, queries.length > 0 && "cursor-pointer")}
      onClick={() => {
        if (queries.length > 0) onSelect(row);
      }}
    >
      <td className="pl-5">
        <div className="flex items-center gap-2 whitespace-nowrap">
          <PlatformLogo
            provider={row.platform}
            label={platformMeta.label}
            className="size-6 rounded-md"
          />
          <span className="font-medium">{platformMeta.label}</span>
        </div>
      </td>
      <td className="text-muted-foreground max-w-0 pl-4 pr-8" colSpan={3}>
        {queries.length > 0 ? (
          <ul className="text-foreground flex flex-col gap-1 text-sm">
            {queries.map((query) => (
              <li key={query} className="truncate">
                {query}
              </li>
            ))}
          </ul>
        ) : (
          <span className="text-sm">{depthLabel}</span>
        )}
      </td>
      <td className="px-4 text-sm font-medium tabular-nums whitespace-nowrap">{depthLabel}</td>
      <td className="text-foreground px-4 whitespace-nowrap tabular-nums" style={DATE_CELL_STYLE}>
        {formatSentimentDateTime(row.created_at)}
      </td>
    </tr>
  );
}

export function PromptDetailResponseTable({
  activeTab,
  data,
  chatResponses = [],
  chatTotal = 0,
  chatPage = 1,
  chatPageSize = DEFAULT_TABLE_PAGE_SIZE,
  onChatPageChange,
  onChatPageSizeChange,
  rankSort = null,
  onRankSortChange,
  promptText,
  loading = false,
  fetching = false,
}: PromptDetailResponseTableProps) {
  const [citationPage, setCitationPage] = useState(1);
  const [citationPageSize, setCitationPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);
  const [expansionPage, setExpansionPage] = useState(1);
  const [expansionPageSize, setExpansionPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);
  const [selectedRow, setSelectedRow] = useState<PromptDetailResponseRow | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const citationRows = useMemo(
    () => promptDetailResponsesForTab(data, "citation"),
    [data],
  );
  const expansionRows = useMemo(
    () => promptDetailResponsesForTab(data, "queryExpansion"),
    [data],
  );

  const sortedCitationRows = useMemo(() => {
    if (!rankSort) return citationRows;
    return [...citationRows].sort((a, b) => compareByRank(a, b, rankSort));
  }, [citationRows, rankSort]);

  const citationPageRows = useMemo(
    () => paginateRows(sortedCitationRows, citationPage, citationPageSize),
    [sortedCitationRows, citationPage, citationPageSize],
  );
  const expansionPageRows = useMemo(
    () => paginateRows(expansionRows, expansionPage, expansionPageSize),
    [expansionRows, expansionPage, expansionPageSize],
  );

  const isChatTab = activeTab === "chat";
  const isExpansionTab = activeTab === "queryExpansion";
  const displayRows = isChatTab
    ? chatResponses
    : isExpansionTab
      ? expansionPageRows
      : citationPageRows;
  const paginationTotal = isChatTab
    ? chatTotal
    : isExpansionTab
      ? expansionRows.length
      : sortedCitationRows.length;
  const paginationPage = isChatTab ? chatPage : isExpansionTab ? expansionPage : citationPage;
  const paginationPageSize = isChatTab
    ? chatPageSize
    : isExpansionTab
      ? expansionPageSize
      : citationPageSize;

  useEffect(() => {
    setCitationPage(1);
    setExpansionPage(1);
  }, [activeTab, data, rankSort]);

  const emptyLabel =
    PROMPT_DETAIL_RESPONSE_TABS.find((tab) => tab.id === activeTab)?.label ?? "数据";

  const selectRow = (nextRow: PromptDetailResponseRow) => {
    setSelectedRow(nextRow);
    setDialogOpen(true);
  };

  return (
    <>
      <TableScrollOverlay fetching={fetching}>
        <table
          className={performanceTableClasses.topicTable}
          style={{ minWidth: PROMPT_DETAIL_RESPONSE_TABLE_MIN_WIDTH }}
        >
        <colgroup>
          {PROMPT_DETAIL_RESPONSE_TABLE_COLUMNS.map((column) => (
            <col key={column.id} style={promptDetailResponseColumnColStyle(column)} />
          ))}
        </colgroup>
        <thead className={performanceTableClasses.head}>
          <tr>
            <th className="pl-5">平台</th>
            <th colSpan={isExpansionTab ? 3 : 1}>{isExpansionTab ? "联网检索词" : "回复"}</th>
            {isExpansionTab ? (
              <th>扇出深度</th>
            ) : (
              <>
                <th>
                  <span className="inline-flex items-center gap-1">
                    提及品牌
                    <ColumnHelp
                      label="提及品牌"
                      description="AI 回复正文中提及的品牌列表。"
                    />
                  </span>
                </th>
                <th>
                  <span className="inline-flex items-center gap-1">
                    是否提及
                    <ColumnHelp
                      label="是否提及"
                      description="AI 回复正文中是否提及当前品牌。"
                    />
                  </span>
                </th>
                <th>
                  <RankSortableHeader
                    label="提及排名"
                    sort={rankSort}
                    onSort={() => onRankSortChange?.(cycleRankSort(rankSort))}
                    help={{
                      label: "提及排名",
                      description: "AI 回复正文中当前品牌的排名。",
                    }}
                  />
                </th>
              </>
            )}
            <th style={DATE_CELL_STYLE}>日期</th>
          </tr>
        </thead>
        <tbody>
          {loading && displayRows.length === 0 ? (
            <SkeletonRows />
          ) : paginationTotal === 0 ? (
            <tr>
              <td colSpan={6} className="text-muted-foreground px-5 py-10 text-center text-sm">
                暂无{emptyLabel}数据
              </td>
            </tr>
          ) : (
            displayRows.map((row) =>
              isExpansionTab ? (
                <QueryExpansionRow key={row.response_id} row={row} onSelect={selectRow} />
              ) : (
                <ResponseRow key={row.response_id} row={row} onSelect={selectRow} />
              ),
            )
          )}
        </tbody>
        </table>
      </TableScrollOverlay>

      <PromptDetailResponseDialog
        row={selectedRow}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        promptText={promptText}
      />

      {paginationTotal > 0 ? (
        <TablePagination
          total={paginationTotal}
          page={paginationPage}
          pageSize={paginationPageSize}
          pageSizeOptions={TABLE_PAGE_SIZE_OPTIONS}
          onPageChange={(nextPage) => {
            if (isChatTab) {
              onChatPageChange?.(nextPage);
              return;
            }
            if (isExpansionTab) {
              setExpansionPage(nextPage);
              return;
            }
            setCitationPage(nextPage);
          }}
          onPageSizeChange={(nextPageSize) => {
            if (isChatTab) {
              onChatPageSizeChange?.(nextPageSize);
              return;
            }
            if (isExpansionTab) {
              setExpansionPageSize(nextPageSize);
              setExpansionPage(1);
              return;
            }
            setCitationPageSize(nextPageSize);
            setCitationPage(1);
          }}
        />
      ) : null}
    </>
  );
}
