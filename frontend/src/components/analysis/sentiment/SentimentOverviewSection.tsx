import { CircleHelp } from "lucide-react";
import { useMemo, useState } from "react";

import { AnalysisRankTable, type RankRow } from "@/components/analysis/common/AnalysisRankTable";
import { buildBrandRankIcon } from "@/components/analysis/common/BrandRankIcon";
import { SentimentMetricCell } from "@/components/analysis/prompt/PerformanceMetricCells";
import { SentimentDistributionChart } from "@/components/analysis/sentiment/SentimentDistributionChart";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import {
  SENTIMENT_RANK_TABLE_HEIGHT,
  SENTIMENT_SECTION_HEIGHT,
  type SentimentOverviewData,
} from "@/lib/analysis/sentiment";
import { cn } from "@/lib/utils";

const DISTRIBUTION_DESCRIPTION =
  "AI 在回答中提及当前品牌时的情感倾向评分（正面/中立/负面），反映了 AI 模型对当前品牌产品或服务的评价态度与推荐意愿，数值越高品牌推荐越正向";

type SentimentOverviewSectionProps = {
  overview: SentimentOverviewData;
  loading?: boolean;
};

function DistributionTitleInfo() {
  const [open, setOpen] = useState(false);

  return (
    <Tooltip open={open} onOpenChange={setOpen}>
      <TooltipTrigger asChild>
        <button
          type="button"
          className="text-muted-foreground hover:text-foreground inline-flex shrink-0 rounded-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          aria-label="了解情感分布"
          onClick={() => setOpen((prev) => !prev)}
        >
          <CircleHelp className="size-4" aria-hidden />
        </button>
      </TooltipTrigger>
      <TooltipContent
        side="top"
        sideOffset={8}
        className="max-w-[240px] px-3 py-2.5 text-sm font-medium leading-relaxed text-left text-wrap"
      >
        <p className="w-full text-wrap">{DISTRIBUTION_DESCRIPTION}</p>
      </TooltipContent>
    </Tooltip>
  );
}

function sentimentBadgeClass(label: string): string {
  if (label === "正面") return "text-emerald-600";
  if (label === "负面") return "text-red-600";
  return "text-amber-600";
}

type DistributionCardProps = {
  score: number | null | undefined;
  scoreLabel: string;
  series: SentimentOverviewData["distributionSeries"];
  loading?: boolean;
};

function SentimentDistributionCard({
  score,
  scoreLabel,
  series,
  loading,
}: DistributionCardProps) {
  const scoreText = score != null ? score.toFixed(1) : null;

  return (
    <div
      className="flex min-h-0 min-w-[min(100%,480px)] flex-[3] flex-col p-5"
      style={{ minHeight: SENTIMENT_SECTION_HEIGHT }}
    >
      <div className="border-border flex shrink-0 items-center justify-between gap-4 border-b pb-5">
        <div className="flex min-w-0 items-center gap-1.5">
          <h3 className="text-base font-bold">情感倾向</h3>
          <DistributionTitleInfo />
        </div>
        {scoreText ? (
          <div className="flex shrink-0 items-center gap-2">
            <span className="text-lg font-bold tracking-tight tabular-nums">{scoreText}</span>
            <span className={cn("text-sm font-semibold", sentimentBadgeClass(scoreLabel))}>
              {scoreLabel}
            </span>
          </div>
        ) : loading ? (
          <div className="bg-background h-7 w-24 animate-pulse rounded-md" />
        ) : null}
      </div>
      <div className="mt-4 flex min-h-0 flex-1 flex-col w-full" aria-busy={loading}>
        {loading ? (
          <div className="bg-background/60 min-h-[120px] flex-1 animate-pulse rounded-md" />
        ) : (
          <SentimentDistributionChart series={series} className="w-full" />
        )}
      </div>
    </div>
  );
}

export function SentimentOverviewSection({
  overview,
  loading = false,
}: SentimentOverviewSectionProps) {
  const rankRowsWithIcons = useMemo(
    () =>
      overview.rankRows.map((row: RankRow) => ({
        ...row,
        icon: buildBrandRankIcon(row.domain ?? ""),
      })),
    [overview.rankRows],
  );

  return (
    <div
      className="border-border w-full overflow-hidden rounded-lg border bg-muted-background"
      aria-busy={loading}
    >
      <div className="@container flex flex-wrap items-stretch">
        <SentimentDistributionCard
          score={overview.score}
          scoreLabel={overview.scoreLabel}
          series={overview.distributionSeries}
          loading={loading}
        />
        <div
          className="border-border flex min-w-[min(100%,240px)] flex-[2] flex-col overflow-hidden border-t p-3 @min-[720px]:border-t-0 @min-[720px]:border-l"
          style={{ minHeight: SENTIMENT_SECTION_HEIGHT }}
        >
          <AnalysisRankTable
            embedded
            loading={loading}
            showMoreFooter
            height={SENTIMENT_RANK_TABLE_HEIGHT}
            className="min-h-0"
            title="情感倾向排名"
            entityHeader="品牌"
            valueHeader="情感倾向"
            rows={rankRowsWithIcons}
            renderValue={(row) => (
              <SentimentMetricCell value={row.value} label={row.sentimentLabel} />
            )}
            emptyMessage="暂无品牌排名数据"
          />
        </div>
      </div>
    </div>
  );
}
