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
import { PromptDetailResponseDialog } from "@/components/analysis/prompt/PromptDetailResponseDialog";
import { PlatformLogo } from "@/components/brand/PlatformLogo";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatRank } from "@/lib/analysis/format";
import {
  PROMPT_DETAIL_RESPONSE_TABS,
  promptDetailResponsesForTab,
  type PromptDetailResponseTab,
} from "@/lib/analysis/promptDetail";
import { formatSentimentDateTime } from "@/lib/analysis/sentiment";
import { resolvePlatformMeta } from "@/lib/analysis/shared";
import type { PromptDetailData, PromptDetailResponseRow, SamplingPlatform } from "@/types";
import {
  performanceTableClasses,
  PROMPT_DETAIL_RESPONSE_TABLE_COLUMNS,
  PROMPT_DETAIL_RESPONSE_TABLE_MIN_WIDTH,
} from "@/components/analysis/prompt/performanceTableLayout";
import { cn } from "@/lib/utils";

const TABLE_MIN_HEIGHT = 300;
const SKELETON_ROWS = 6;

type PromptDetailResponseTableProps = {
  activeTab: PromptDetailResponseTab;
  data: PromptDetailData | null;
  platformsMeta: SamplingPlatform[];
  promptText: string;
  loading?: boolean;
};

function MentionStatusCell({ mentioned }: { mentioned: boolean }) {
  return (
    <Badge variant={mentioned ? "success" : "error"} className="px-1.5 py-0.5 font-semibold">
      <span
        className={cn("size-2 shrink-0 rounded-full", mentioned ? "bg-success" : "bg-error")}
        aria-hidden
      />
      {mentioned ? "是" : "否"}
    </Badge>
  );
}

function SkeletonRows() {
  return (
    <>
      {Array.from({ length: SKELETON_ROWS }).map((_, index) => (
        <tr key={index} className="border-border border-t [&>td]:py-3" aria-hidden>
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
            <Skeleton className="h-5 w-12 rounded-full" />
          </td>
          <td>
            <Skeleton className="h-4 w-10" />
          </td>
          <td>
            <Skeleton className="h-4 w-28" />
          </td>
        </tr>
      ))}
    </>
  );
}

function ResponseRow({
  row,
  platformsMeta,
  onSelect,
}: {
  row: PromptDetailResponseRow;
  platformsMeta: SamplingPlatform[];
  onSelect: (row: PromptDetailResponseRow) => void;
}) {
  const platformMeta = resolvePlatformMeta(row.platform, platformsMeta);

  return (
    <tr
      className="border-border hover:bg-muted/40 cursor-pointer border-t [&>td]:py-3"
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
      <td className="max-w-0 pl-4 pr-8">
        <PromptTextCell text={row.reply_preview || "—"} tooltipMaxLength={120} />
      </td>
      <td className="px-4">
        <MentionStatusCell mentioned={row.mentioned} />
      </td>
      <td className="px-4 font-semibold tabular-nums">
        {row.rank != null ? formatRank(row.rank) : "—"}
      </td>
      <td className="text-foreground px-4 whitespace-nowrap tabular-nums">
        {formatSentimentDateTime(row.created_at)}
      </td>
    </tr>
  );
}

export function PromptDetailResponseTable({
  activeTab,
  data,
  platformsMeta,
  promptText,
  loading = false,
}: PromptDetailResponseTableProps) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);
  const [selectedRow, setSelectedRow] = useState<PromptDetailResponseRow | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const rows = useMemo(
    () => promptDetailResponsesForTab(data, activeTab),
    [data, activeTab],
  );

  const pageRows = useMemo(
    () => paginateRows(rows, page, pageSize),
    [rows, page, pageSize],
  );

  useEffect(() => {
    setPage(1);
  }, [activeTab, data]);

  const emptyLabel =
    PROMPT_DETAIL_RESPONSE_TABS.find((tab) => tab.id === activeTab)?.label ?? "数据";

  return (
    <div className="overflow-x-auto" style={{ minHeight: TABLE_MIN_HEIGHT }}>
      <table
        className={performanceTableClasses.topicTable}
        style={{ minWidth: PROMPT_DETAIL_RESPONSE_TABLE_MIN_WIDTH }}
      >
        <colgroup>
          {PROMPT_DETAIL_RESPONSE_TABLE_COLUMNS.map((column) => (
            <col key={column.id} style={{ width: column.width }} />
          ))}
        </colgroup>
        <thead className={performanceTableClasses.head}>
          <tr>
            <th className="pl-5">平台</th>
            <th>回复</th>
            <th>
              <span className="inline-flex items-center gap-1">
                是否提及
                <ColumnHelp
                  label="是否提及"
                  description="AI 回复正文中是否提及自有品牌。"
                />
              </span>
            </th>
            <th>
              <span className="inline-flex items-center gap-1">
                平均排名
                <ColumnHelp
                  label="平均排名"
                  description="该条回复中自有品牌在 AI 回答里的出现顺位。"
                />
              </span>
            </th>
            <th>日期</th>
          </tr>
        </thead>
        <tbody className={performanceTableClasses.row}>
          {loading ? (
            <SkeletonRows />
          ) : activeTab === "queryExpansion" ? (
            <tr>
              <td
                colSpan={5}
                className="text-muted-foreground px-4 text-center align-middle"
                style={{ height: TABLE_MIN_HEIGHT - 40 }}
              >
                暂无查询扩展数据
              </td>
            </tr>
          ) : rows.length === 0 ? (
            <tr>
              <td
                colSpan={5}
                className="text-muted-foreground px-4 text-center align-middle"
                style={{ height: TABLE_MIN_HEIGHT - 40 }}
              >
                暂无{emptyLabel}数据
              </td>
            </tr>
          ) : (
            pageRows.map((row) => (
              <ResponseRow
                key={row.response_id}
                row={row}
                platformsMeta={platformsMeta}
                onSelect={(nextRow) => {
                  setSelectedRow(nextRow);
                  setDialogOpen(true);
                }}
              />
            ))
          )}
        </tbody>
      </table>

      <PromptDetailResponseDialog
        row={selectedRow}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        promptText={promptText}
        platformsMeta={platformsMeta}
      />

      {!loading && activeTab !== "queryExpansion" && rows.length > 0 ? (
        <TablePagination
          total={rows.length}
          page={page}
          pageSize={pageSize}
          pageSizeOptions={TABLE_PAGE_SIZE_OPTIONS}
          onPageChange={setPage}
          onPageSizeChange={(nextPageSize) => {
            setPageSize(nextPageSize);
            setPage(1);
          }}
        />
      ) : null}
    </div>
  );
}
