import { useEffect, useMemo, useState } from "react";

import {
  DEFAULT_TABLE_PAGE_SIZE,
  paginateRows,
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import { PromptDetailResponseDialog } from "@/components/analysis/prompt/PromptDetailResponseDialog";
import { PromptTextCell, SentimentMetricCell } from "@/components/analysis/prompt/PerformanceMetricCells";
import { PlatformLogo } from "@/components/brand/PlatformLogo";
import { Skeleton } from "@/components/ui/skeleton";
import { resolvePlatformMeta } from "@/lib/analysis/shared";
import {
  filterSentimentResponses,
  formatSentimentDateTime,
  sentimentLabelFromTab,
} from "@/lib/analysis/sentiment";
import type { LlmResponseDialogRow, SamplingPlatform, SentimentResponseRow, SentimentTab } from "@/types";

const SENTIMENT_RESPONSE_SKELETON_ROWS = 6;
/** 约 6 行数据 + 表头的可视最小高度 */
const SENTIMENT_RESPONSE_TABLE_MIN_HEIGHT = 300;

type SentimentResponseTableProps = {
  activeTab: SentimentTab;
  responses: SentimentResponseRow[];
  platformsMeta: SamplingPlatform[];
  loading?: boolean;
};

function SentimentResponseSkeletonRows() {
  return (
    <>
      {Array.from({ length: SENTIMENT_RESPONSE_SKELETON_ROWS }).map((_, rowIndex) => (
        <tr key={rowIndex} className="border-border border-t [&>td]:py-3" aria-hidden>
          <td className="pl-5">
            <div className="flex items-center gap-2">
              <Skeleton className="size-6 rounded-md" />
              <Skeleton className="h-4 w-20" />
            </div>
          </td>
          <td className="px-4">
            <Skeleton className="h-4 w-4/5" />
          </td>
          <td className="px-4">
            <Skeleton className="h-4 w-12" />
          </td>
          <td className="px-4">
            <Skeleton className="h-4 w-full max-w-[280px]" />
          </td>
          <td className="px-4">
            <Skeleton className="h-4 w-36" />
          </td>
        </tr>
      ))}
    </>
  );
}

export function SentimentResponseTable({
  activeTab,
  responses,
  platformsMeta,
  loading = false,
}: SentimentResponseTableProps) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);
  const [selectedRow, setSelectedRow] = useState<LlmResponseDialogRow | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [promptText, setPromptText] = useState("");

  const openResponseDialog = (row: SentimentResponseRow) => {
    setSelectedRow({
      response_id: row.response_id,
      platform: row.platform,
      reply_preview: row.reply_preview,
    });
    setPromptText(row.prompt_text);
    setDialogOpen(true);
  };

  const filteredRows = useMemo(
    () => filterSentimentResponses(responses, activeTab),
    [responses, activeTab],
  );

  const pageRows = useMemo(
    () => paginateRows(filteredRows, page, pageSize),
    [filteredRows, page, pageSize],
  );

  useEffect(() => {
    setPage(1);
  }, [activeTab, responses]);

  const handlePageSizeChange = (nextPageSize: number) => {
    setPageSize(nextPageSize);
    setPage(1);
  };

  const emptyLabel =
    activeTab === "positive" ? "正面" : activeTab === "neutral" ? "中立" : "负面";

  return (
    <div
      className="border-border overflow-hidden rounded-lg border bg-white"
      aria-busy={loading}
    >
      <div
        className="overflow-x-auto"
        style={{ minHeight: SENTIMENT_RESPONSE_TABLE_MIN_HEIGHT }}
      >
        <table className="w-full min-w-[720px] table-auto text-sm">
          <thead className="text-muted-foreground bg-muted/80 text-left">
            <tr className="[&>th]:whitespace-nowrap [&>th]:px-4 [&>th]:py-2.5 [&>th]:font-medium">
              <th className="pl-5">平台</th>
              <th>提示词</th>
              <th>情感倾向</th>
              <th>回复</th>
              <th>日期</th>
            </tr>
          </thead>
          <tbody className="border-border border-t">
            {loading ? (
              <SentimentResponseSkeletonRows />
            ) : filteredRows.length === 0 ? (
              <tr>
                <td
                  colSpan={5}
                  className="text-muted-foreground px-4 text-center align-middle"
                  style={{ height: SENTIMENT_RESPONSE_TABLE_MIN_HEIGHT - 40 }}
                >
                  暂无{emptyLabel}情感数据
                </td>
              </tr>
            ) : (
              pageRows.map((row) => {
                const platformMeta = resolvePlatformMeta(row.platform, platformsMeta);
                const sentimentLabel = sentimentLabelFromTab(row.sentiment);
                return (
                  <tr
                    key={row.response_id}
                    className="border-border hover:bg-muted/40 cursor-pointer border-t [&>td]:py-3"
                    onClick={() => openResponseDialog(row)}
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
                    <td className="max-w-[220px] px-4">
                      <PromptTextCell text={row.prompt_text || "—"} />
                    </td>
                    <td className="px-4">
                      <SentimentMetricCell value={sentimentLabel} delta={null} />
                    </td>
                    <td className="max-w-[320px] px-4">
                      <PromptTextCell text={row.reply_preview || "—"} />
                    </td>
                    <td className="text-muted-foreground px-4 whitespace-nowrap tabular-nums">
                      {formatSentimentDateTime(row.created_at)}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {!loading && filteredRows.length > 0 ? (
        <TablePagination
          total={filteredRows.length}
          page={page}
          pageSize={pageSize}
          pageSizeOptions={TABLE_PAGE_SIZE_OPTIONS}
          onPageChange={setPage}
          onPageSizeChange={handlePageSizeChange}
        />
      ) : null}

      <PromptDetailResponseDialog
        row={selectedRow}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        promptText={promptText}
        platformsMeta={platformsMeta}
      />
    </div>
  );
}
