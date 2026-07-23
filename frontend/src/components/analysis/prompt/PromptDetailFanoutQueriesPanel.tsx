import { useEffect, useState } from "react";

import {
  DEFAULT_TABLE_PAGE_SIZE,
  TABLE_PAGE_SIZE_OPTIONS,
  TablePagination,
} from "@/components/analysis/common/TablePagination";
import {
  ColumnHelp,
  PromptTextCell,
} from "@/components/analysis/prompt/PerformanceMetricCells";
import { PerformanceTableShell } from "@/components/analysis/prompt/PerformanceTableShell";
import {
  FANOUT_QUERY_TABLE_COLUMN_COUNT,
  FANOUT_QUERY_TABLE_COLUMNS,
  FANOUT_QUERY_TABLE_MIN_WIDTH,
  performanceTableClasses,
} from "@/components/analysis/prompt/performanceTableLayout";
import { PlatformLogoGroup } from "@/components/brand/PlatformLogo";
import { Skeleton } from "@/components/ui/skeleton";
import { useFanoutQueries } from "@/hooks/useFanoutAnalysis";
import { formatCount, formatRate } from "@/lib/analysis/format";
import type { AnalysisFilters } from "@/types";

type PromptDetailFanoutQueriesPanelProps = {
  subjectId: string;
  promptId: string;
  filters: AnalysisFilters;
};

function platformIdsForItem(platforms: string[], counts?: Record<string, number>): string[] {
  if (counts && Object.keys(counts).length > 0) {
    return Object.entries(counts)
      .filter(([, count]) => count > 0)
      .sort((a, b) => b[1] - a[1])
      .map(([id]) => id);
  }
  return platforms;
}

function FanoutQuerySkeletonRows() {
  return (
    <>
      {Array.from({ length: 6 }).map((_, index) => (
        <tr key={index} className={performanceTableClasses.row}>
          <td className="pl-5">
            <Skeleton className="h-4 w-3/4 max-w-md" />
          </td>
          <td>
            <Skeleton className="h-5 w-20" />
          </td>
          <td>
            <Skeleton className="h-4 w-8" />
          </td>
          <td>
            <Skeleton className="h-4 w-12" />
          </td>
        </tr>
      ))}
    </>
  );
}

/** 提示词详情 · 查询扇出 Tab：表格分页全部扇出子查询 */
export function PromptDetailFanoutQueriesPanel({
  subjectId,
  promptId,
  filters,
}: PromptDetailFanoutQueriesPanelProps) {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);

  useEffect(() => {
    setPage(1);
  }, [promptId, filters, pageSize]);

  const { isLoading, isFetching, rows, total } = useFanoutQueries(subjectId, promptId, filters, {
    page,
    pageSize,
    enabled: Boolean(promptId),
  });

  return (
    <PerformanceTableShell
      loading={isLoading}
      fetching={isFetching}
      scrollMinWidth={FANOUT_QUERY_TABLE_MIN_WIDTH}
      className="rounded-none border-0"
      footer={
        total > 0 ? (
          <div className="border-border border-t px-3 py-2">
            <TablePagination
              page={page}
              pageSize={pageSize}
              total={total}
              pageSizeOptions={TABLE_PAGE_SIZE_OPTIONS}
              onPageChange={setPage}
              onPageSizeChange={(next) => {
                setPageSize(next);
                setPage(1);
              }}
            />
          </div>
        ) : null
      }
    >
      <table className={performanceTableClasses.topicTable}>
        <colgroup>
          {FANOUT_QUERY_TABLE_COLUMNS.map((column) => (
            <col key={column.id} style={{ width: column.width }} />
          ))}
        </colgroup>
        <thead className={performanceTableClasses.head}>
          <tr>
            <th className="pl-5">名称</th>
            <th>平台</th>
            <th>数量</th>
            <th>
              <div className="inline-flex items-center gap-1">
                <span>贡献率</span>
                <ColumnHelp
                  label="贡献率"
                  description="该子查询出现次数占本提示词全部扇出子查询次数的比例。"
                />
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          {isLoading && rows.length === 0 ? (
            <FanoutQuerySkeletonRows />
          ) : total === 0 ? (
            <tr>
              <td
                colSpan={FANOUT_QUERY_TABLE_COLUMN_COUNT}
                className="text-muted-foreground px-5 py-10 text-center text-sm"
              >
                暂无查询扇出子查询
              </td>
            </tr>
          ) : (
            rows.map((item) => (
              <tr key={item.query} className={performanceTableClasses.row}>
                <td className="text-foreground max-w-0 overflow-hidden pl-5 font-medium">
                  <PromptTextCell text={item.query} />
                </td>
                <td>
                  <PlatformLogoGroup
                    providers={platformIdsForItem(item.platforms, item.platform_counts)}
                    counts={item.platform_counts}
                    logoClassName="size-5"
                  />
                </td>
                <td className="text-foreground font-medium tabular-nums">
                  {formatCount(item.frequency)}
                </td>
                <td className="text-foreground font-medium tabular-nums">
                  {formatRate(item.contribution_rate)}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </PerformanceTableShell>
  );
}
