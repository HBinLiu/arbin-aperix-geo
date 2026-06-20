import { CircleHelp } from "lucide-react";
import { useMemo, useState } from "react";

import { LineChartSkeleton } from "@/components/analysis/common/MetricsSkeleton";
import { SimpleLineChart } from "@/components/analysis/common/SimpleLineChart";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { formatCount, formatRate } from "@/lib/analysis/format";
import type { CitationDomainAnalysisData } from "@/types";

const DOMAIN_COUNT_DESCRIPTION =
  "您的品牌在 AI 生成答案中被该域名引用的次数。";

const DOMAIN_CHART_HEIGHT = 240;

type CitationDomainSectionProps = {
  data: CitationDomainAnalysisData | undefined;
  loading?: boolean;
};

function MetricTitleInfo({ title, description }: { title: string; description: string }) {
  const [open, setOpen] = useState(false);

  return (
    <Tooltip open={open} onOpenChange={setOpen}>
      <TooltipTrigger asChild>
        <button
          type="button"
          className="text-muted-foreground hover:text-foreground inline-flex shrink-0 rounded-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          aria-label={`了解${title}`}
          onClick={() => setOpen((prev) => !prev)}
        >
          <CircleHelp className="size-4" aria-hidden />
        </button>
      </TooltipTrigger>
      <TooltipContent
        side="top"
        sideOffset={8}
        className="w-[250px] min-w-[250px] max-w-[250px] px-3 py-2.5 text-sm font-medium leading-relaxed text-left text-wrap"
      >
        <p className="w-full text-wrap">{description}</p>
      </TooltipContent>
    </Tooltip>
  );
}

export function CitationDomainSection({
  data,
  loading = false,
}: CitationDomainSectionProps) {
  const singleSeries = useMemo(
    () =>
      (data?.series ?? []).map((point) => ({
        date: point.date,
        value: point.count ?? 0,
      })),
    [data?.series],
  );

  return (
    <div
      className="border-border w-full overflow-hidden rounded-lg border bg-white"
      aria-busy={loading}
    >
      <div className="@container flex flex-wrap items-stretch">
        <div className="flex min-w-[min(100%,420px)] max-w-[420px] flex-[2] flex-col justify-between p-8">
          <div>
            <div className="flex items-center gap-1.5">
              <h3 className="text-lg font-bold">总引用次数</h3>
            </div>
            <p className="text-muted-foreground mt-1 max-w-[420px] text-sm leading-snug">
              {DOMAIN_COUNT_DESCRIPTION}
            </p>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-1">
            {loading ? (
              <div className="bg-muted h-8 w-20 animate-pulse rounded-md" />
            ) : (
              <>
                <span className="text-3xl font-bold tracking-tight tabular-nums">
                  {data?.count ?? "-"}
                </span>
                <div className="bg-border mx-1 h-10 w-px shrink-0" aria-hidden />
                <div className="flex flex-col gap-0.5">
                  <span className="text-muted-foreground text-sm">引用率</span>
                  <span className="text-base font-semibold text-success tabular-nums">
                    {formatRate(data?.citation_rate)}
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
        <div className="border-border flex min-w-0 flex-[3] flex-col border-t p-8 @min-[720px]:border-t-0">
          {loading ? (
            <LineChartSkeleton chartHeight={DOMAIN_CHART_HEIGHT} className="w-full" />
          ) : (
            <SimpleLineChart
              className="w-full"
              height={DOMAIN_CHART_HEIGHT}
              singleSeries={singleSeries}
              variant="area"
              yAxisMode="score"
              valueFormatter={formatCount}
              tooltipLabel="引用次数"
            />
          )}
        </div>
      </div>
    </div>
  );
}
