import { Loader2, Sparkles, X } from "lucide-react";

import {
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import {
  PromptTextCell,
} from "@/components/analysis/prompt/PerformanceMetricCells";
import { PerformanceTableShell } from "@/components/analysis/prompt/PerformanceTableShell";
import { performanceTableClasses } from "@/components/analysis/prompt/performanceTableLayout";
import { PlatformLogoGroup } from "@/components/brand/PlatformLogo";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatCount } from "@/lib/analysis/format";
import type { PromptFanoutOpportunityRow } from "@/types";

const COLUMNS = [
  { id: "name", width: "28%" },
  { id: "topic", width: "12%" },
  { id: "frequency", width: "10%" },
  { id: "platforms", width: "16%" },
  { id: "parent", width: "22%" },
  { id: "actions", width: "12%" },
] as const;

function platformIdsFromCounts(counts: Record<string, number>): string[] {
  return Object.entries(counts)
    .filter(([, count]) => count > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([id]) => id);
}

function SkeletonRows({ count = 5 }: { count?: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <tr key={index} className={performanceTableClasses.row} aria-hidden>
          <td className="pl-5">
            <Skeleton className="h-4 w-3/4 max-w-xs" />
          </td>
          <td>
            <Skeleton className="h-4 w-16" />
          </td>
          <td>
            <Skeleton className="h-4 w-8" />
          </td>
          <td>
            <Skeleton className="h-5 w-20" />
          </td>
          <td>
            <Skeleton className="h-4 w-40" />
          </td>
          <td>
            <Skeleton className="h-8 w-28" />
          </td>
        </tr>
      ))}
    </>
  );
}

type OpportunityPromptFanoutTableProps = {
  rows: PromptFanoutOpportunityRow[];
  loading?: boolean;
  fetching?: boolean;
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  promotingId?: string | null;
  dismissingId?: string | null;
  onPromote: (row: PromptFanoutOpportunityRow) => void;
  onDismiss: (row: PromptFanoutOpportunityRow) => void;
};

/** 潜在提示词机会表：名称 / 主题 / 出现次数 / 平台 / 来源提示词 / 操作 */
export function OpportunityPromptFanoutTable({
  rows,
  loading = false,
  fetching = false,
  total,
  page,
  pageSize,
  onPageChange,
  onPageSizeChange,
  promotingId = null,
  dismissingId = null,
  onPromote,
  onDismiss,
}: OpportunityPromptFanoutTableProps) {
  return (
    <PerformanceTableShell
      loading={loading}
      fetching={fetching}
      scrollMinWidth={960}
      footer={
        total > 0 ? (
          <TablePagination
            page={page}
            pageSize={pageSize}
            total={total}
            pageSizeOptions={TABLE_PAGE_SIZE_OPTIONS}
            onPageChange={onPageChange}
            onPageSizeChange={(next) => {
              onPageSizeChange(next);
              onPageChange(1);
            }}
          />
        ) : null
      }
    >
      <table className={performanceTableClasses.topicTable}>
        <colgroup>
          {COLUMNS.map((column) => (
            <col key={column.id} style={{ width: column.width }} />
          ))}
        </colgroup>
        <thead className={performanceTableClasses.head}>
          <tr>
            <th className="pl-5">名称</th>
            <th>主题</th>
            <th>出现次数</th>
            <th>平台</th>
            <th>来源提示词</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {loading && rows.length === 0 ? (
            <SkeletonRows />
          ) : total === 0 ? (
            <tr>
              <td
                colSpan={COLUMNS.length}
                className="text-muted-foreground px-5 py-10 text-center text-sm"
              >
                暂无潜在提示词
              </td>
            </tr>
          ) : (
            rows.map((row) => {
              const busyPromote = promotingId === row.id;
              const busyDismiss = dismissingId === row.id;
              const busy = busyPromote || busyDismiss;
              return (
                <tr key={row.id} className={performanceTableClasses.row}>
                  <td className="text-foreground max-w-0 overflow-hidden pl-5 font-medium">
                    <PromptTextCell text={row.query_text} />
                  </td>
                  <td className="text-foreground max-w-0 overflow-hidden">
                    <span className="block truncate">{row.topic_name || "—"}</span>
                  </td>
                  <td className="text-foreground font-medium tabular-nums">
                    {formatCount(row.frequency)}
                  </td>
                  <td>
                    <PlatformLogoGroup
                      providers={platformIdsFromCounts(row.platform_counts)}
                      counts={row.platform_counts}
                      logoClassName="size-5"
                    />
                  </td>
                  <td className="text-foreground max-w-0 overflow-hidden">
                    <PromptTextCell text={row.parent_prompt_text} />
                  </td>
                  <td>
                    <div className="flex items-center gap-1.5">
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        className="h-8 gap-1 px-2.5 text-xs"
                        disabled={busy}
                        onClick={() => onPromote(row)}
                      >
                        {busyPromote ? (
                          <Loader2 className="size-3.5 animate-spin" aria-hidden />
                        ) : (
                          <Sparkles className="size-3.5" aria-hidden />
                        )}
                        升级
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        className="text-muted-foreground h-8 gap-1 px-2 text-xs"
                        disabled={busy}
                        onClick={() => onDismiss(row)}
                      >
                        {busyDismiss ? (
                          <Loader2 className="size-3.5 animate-spin" aria-hidden />
                        ) : (
                          <X className="size-3.5" aria-hidden />
                        )}
                        忽略
                      </Button>
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
