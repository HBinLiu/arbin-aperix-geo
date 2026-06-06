import { Skeleton } from "@/components/ui/skeleton";

type LineChartSkeletonProps = {
  chartHeight?: number;
  className?: string;
};

/** 折线图绘图区骨架 */
export function LineChartSkeleton({ chartHeight = 270, className }: LineChartSkeletonProps) {
  return (
    <div className={className} style={{ minHeight: chartHeight }} aria-hidden>
      <div className="flex h-full flex-col gap-3">
        <div className="flex min-h-0 flex-1 gap-2">
          <div className="flex shrink-0 flex-col justify-between py-1">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-3 w-9" />
            ))}
          </div>
          <Skeleton
            className="flex-1 rounded-lg"
            style={{ height: chartHeight - 50 }}
          />
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
};

/** 排名表 tbody + 页脚骨架 */
export function RankTableSkeleton({ showMoreFooter = false }: RankTableSkeletonProps) {
  return (
    <div className="flex flex-col gap-0" aria-hidden>
      <div className="min-h-0 flex-1 space-y-0 px-2">
        <div className="grid grid-cols-[2.5rem_minmax(0,1fr)_4.5rem_3.5rem] gap-x-2 px-2 py-2">
          <Skeleton className="h-3 w-4" />
          <Skeleton className="h-3 w-8" />
          <Skeleton className="h-3 w-10" />
          <Skeleton className="h-3 w-8" />
        </div>
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="border-border grid grid-cols-[2.5rem_minmax(0,1fr)_4.5rem_3.5rem] items-center gap-x-2 border-t px-2 py-2"
          >
            <Skeleton className="h-3 w-5" />
            <div className="flex min-w-0 items-center gap-2">
              <Skeleton className="size-6 shrink-0 rounded-md" />
              <Skeleton className="h-3 w-24 max-w-full" />
            </div>
            <Skeleton className="h-3 w-10" />
            <Skeleton className="h-3 w-8" />
          </div>
        ))}
      </div>
      {showMoreFooter ? (
        <div className="mt-6 shrink-0 px-4 py-2">
          <Skeleton className="h-9 w-full rounded-lg" />
        </div>
      ) : null}
    </div>
  );
}
