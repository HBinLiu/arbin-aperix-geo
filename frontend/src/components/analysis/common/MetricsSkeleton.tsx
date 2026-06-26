import { compactTableRowClass } from "@/components/analysis/prompt/performanceTableLayout";
import { rankTableColWidths, RANK_TABLE_MIN_WIDTH } from "@/components/analysis/common/analysisRankTableLayout";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

type LineChartSkeletonProps = {
  chartHeight?: number;
  className?: string;
};

/** 折线图绘图区骨架 */
export function LineChartSkeleton({ chartHeight, className }: LineChartSkeletonProps) {
  const fixedHeight = chartHeight != null;
  return (
    <div
      className={cn(!fixedHeight && "min-h-[120px] flex-1", className)}
      style={fixedHeight ? { minHeight: chartHeight } : undefined}
      aria-hidden
    >
      <div className="flex h-full min-h-[120px] flex-col gap-3">
        <div className="flex min-h-0 flex-1 gap-2">
          <div className="flex shrink-0 flex-col justify-between py-1">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-3 w-9" />
            ))}
          </div>
          <Skeleton className="min-h-[120px] flex-1 rounded-lg" />
        </div>
        <div className="flex justify-between pl-11 pr-1">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-3 w-10" />
          ))}
        </div>
        <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1.5">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex items-center gap-1.5">
              <Skeleton className="size-2 rounded-[2px]" />
              <Skeleton className="h-3 w-12" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

type RankTableSkeletonProps = {
  showMoreFooter?: boolean;
  showDeltaColumn?: boolean;
};

function RankTableColGroup({ showDeltaColumn = true }: { showDeltaColumn?: boolean }) {
  const cols = rankTableColWidths(showDeltaColumn);
  return (
    <colgroup>
      <col style={{ width: cols.index }} />
      <col style={{ width: cols.brand }} />
      <col style={{ width: cols.value }} />
      {cols.delta ? <col style={{ width: cols.delta }} /> : null}
    </colgroup>
  );
}

/** 排名表 tbody + 页脚骨架（与 AnalysisRankTable 同 table/colgroup 结构，避免 grid 百分比换行） */
export function RankTableSkeleton({
  showMoreFooter = false,
  showDeltaColumn = true,
}: RankTableSkeletonProps) {
  return (
    <div className="flex flex-col gap-0" aria-hidden>
      <div className="min-h-0 flex-1 overflow-x-auto overflow-y-auto">
        <table
          className="w-full table-fixed text-sm"
          style={{ minWidth: RANK_TABLE_MIN_WIDTH }}
        >
          <RankTableColGroup showDeltaColumn={showDeltaColumn} />
          <thead className="text-muted-foreground text-left text-xs">
            <tr className="border-border border-b [&>th]:whitespace-nowrap [&>th]:py-2">
              <th className="px-2 pl-4 font-medium">
                <Skeleton className="h-3 w-4" />
              </th>
              <th className="px-4 font-medium">
                <Skeleton className="h-3 w-8" />
              </th>
              <th className="px-4 font-medium">
                <Skeleton className="h-3 w-10" />
              </th>
              {showDeltaColumn ? (
                <th className="px-4 font-medium">
                  <Skeleton className="h-3 w-8" />
                </th>
              ) : null}
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: 5 }).map((_, i) => (
              <tr key={i} className={compactTableRowClass}>
                <td className="px-2 pl-4">
                  <Skeleton className="h-3 w-5" />
                </td>
                <td className="min-w-0 overflow-hidden px-4">
                  <div className="flex min-w-0 items-center gap-2">
                    <Skeleton className="size-6 shrink-0 rounded-md" />
                    <Skeleton className="h-3 max-w-full min-w-0 flex-1" />
                  </div>
                </td>
                <td className="px-4">
                  <Skeleton className="h-3 w-10" />
                </td>
                {showDeltaColumn ? (
                  <td className="px-4">
                    <Skeleton className="h-3 w-8" />
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {showMoreFooter ? (
        <div className={cn("shrink-0 px-4 py-2", showMoreFooter && "mt-0")}>
          <Skeleton className="h-9 w-full rounded-lg" />
        </div>
      ) : null}
    </div>
  );
}
