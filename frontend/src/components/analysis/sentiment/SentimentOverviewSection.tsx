import { CircleHelp } from "lucide-react";
import { useMemo, useState } from "react";

import { AnalysisRankTable, type RankRow } from "@/components/analysis/common/AnalysisRankTable";
import { SentimentMetricCell } from "@/components/analysis/prompt/PerformanceMetricCells";
import { SentimentDistributionChart } from "@/components/analysis/sentiment/SentimentDistributionChart";
import { PlatformLogo } from "@/components/brand/PlatformLogo";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import {
  SENTIMENT_CHART_HEIGHT,
  SENTIMENT_RANK_TABLE_HEIGHT,
  SENTIMENT_SECTION_HEIGHT,
  type SentimentOverviewData,
} from "@/lib/analysis/sentiment";
import type { SentimentDistributionPoint } from "@/types";
import { cn } from "@/lib/utils";

const DISTRIBUTION_DESCRIPTION =
  "统计 AI 回复中提及自有品牌时的情感分布，按日展示正面、中立与负面占比。";

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
        className="w-[250px] min-w-[250px] max-w-[250px] px-3 py-2.5 text-sm font-medium leading-relaxed text-left text-wrap"
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
  series: SentimentDistributionPoint[];
  loading?: boolean;
};

function SentimentDistributionCard({ score, scoreLabel, series, loading }: DistributionCardProps) {
  const points = score != null ? (score <= 1 ? score * 100 : score) : null;
  const scoreText = points != null ? points.toFixed(1) : null;

  return (
    <div className="flex min-w-[min(100%,480px)] flex-[3] flex-col p-5" style={{ minHeight: SENTIMENT_SECTION_HEIGHT }}>
      <div className="border-border flex shrink-0 items-center justify-between gap-4 border-b pb-5">
        <div className="flex min-w-0 items-center gap-1.5">
          <h3 className="text-base font-bold">情感分布</h3>
          <DistributionTitleInfo />
        </div>
        {scoreText ? (
          <div className="flex shrink-0 items-baseline gap-2">
            <span className="text-lg font-bold tracking-tight tabular-nums">{scoreText}</span>
            <span className={cn("text-sm font-semibold", sentimentBadgeClass(scoreLabel))}>
              {scoreLabel}
            </span>
          </div>
        ) : loading ? (
          <div className="bg-muted h-7 w-24 animate-pulse rounded-md" />
        ) : null}
      </div>
      <div className="mt-4 min-w-0 w-full" style={{ minHeight: SENTIMENT_CHART_HEIGHT }} aria-busy={loading}>
        {loading ? (
          <div
            className="bg-muted/60 w-full animate-pulse rounded-md"
            style={{ height: SENTIMENT_CHART_HEIGHT }}
          />
        ) : (
          <SentimentDistributionChart series={series} height={SENTIMENT_CHART_HEIGHT} className="w-full" />
        )}
      </div>
    </div>
  );
}

export function SentimentOverviewSection({ overview, loading = false }: SentimentOverviewSectionProps) {
  const rankRowsWithIcons = useMemo(
    () =>
      overview.rankRows.map((row: RankRow) => ({
        ...row,
        icon: (
          <PlatformLogo
            provider={row.id}
            label={row.label}
            className="size-6 rounded-md"
          />
        ),
      })),
    [overview.rankRows],
  );

  return (
    <div
      className="border-border w-full overflow-hidden rounded-lg border bg-white"
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
            title="情感分布排名"
            entityHeader="平台"
            valueHeader="情感倾向分数"
            rows={rankRowsWithIcons}
            renderValue={(row) => <SentimentMetricCell value={row.value} delta={null} />}
            emptyMessage="暂无平台排名数据"
          />
        </div>
      </div>
    </div>
  );
}
