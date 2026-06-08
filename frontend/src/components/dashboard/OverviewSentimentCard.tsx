import { CircleHelp } from "lucide-react";
import { useState } from "react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { sentimentLabelFromScore } from "@/lib/analysis/sentiment";
import { cn } from "@/lib/utils";

type OverviewSentimentCardProps = {
  description: string;
  score: number | null | undefined;
  loading?: boolean;
  className?: string;
};

function sentimentTextClass(label: string): string {
  if (label === "正面") return "text-emerald-600";
  if (label === "负面") return "text-red-600";
  return "text-amber-600";
}

function sentimentBarClass(label: string): string {
  if (label === "正面") return "bg-emerald-500";
  if (label === "负面") return "bg-red-500";
  return "bg-amber-500";
}

function MetricTitleInfo({ description }: { description: string }) {
  const [open, setOpen] = useState(false);

  return (
    <Tooltip open={open} onOpenChange={setOpen}>
      <TooltipTrigger asChild>
        <button
          type="button"
          className="text-muted-foreground hover:text-foreground inline-flex shrink-0 rounded-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          aria-label="了解情感倾向"
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

export function OverviewSentimentCard({
  description,
  score,
  loading = false,
  className,
}: OverviewSentimentCardProps) {
  const label = sentimentLabelFromScore(score);
  const points = score != null ? (score <= 1 ? score * 100 : score) : null;
  const scoreText = points != null ? points.toFixed(1) : "-";
  const progress = points != null ? Math.min(100, Math.max(0, points)) : 0;

  return (
    <div
      className={cn(
        "border-border flex min-h-[120px] flex-col rounded-lg border bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04)]",
        className,
      )}
      aria-busy={loading}
    >
      <div className="flex items-center gap-1.5">
        <h3 className="text-sm font-medium text-foreground">情感倾向</h3>
        <MetricTitleInfo description={description} />
      </div>

      {loading ? (
        <>
          <div className="bg-muted mt-4 h-8 w-32 animate-pulse rounded-md" />
          <div className="bg-muted mt-4 h-2 w-full animate-pulse rounded-full" />
        </>
      ) : (
        <>
          <div className="mt-3 flex items-baseline gap-2">
            <span className={cn("text-2xl font-bold tracking-tight", sentimentTextClass(label))}>
              {label}
            </span>
            <span className="inline-flex items-center gap-1.5 text-sm font-semibold tabular-nums">
              <span
                className={cn("inline-block size-2 rounded-full", sentimentBarClass(label))}
                aria-hidden
              />
              {scoreText}
            </span>
          </div>
          <div
            className="bg-muted mt-4 h-2 w-full overflow-hidden rounded-full"
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`情感得分 ${scoreText}`}
          >
            <div
              className={cn("h-full rounded-full transition-all", sentimentBarClass(label))}
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className={cn("mt-2 text-xs font-medium", sentimentTextClass(label))}>{label}</p>
        </>
      )}
    </div>
  );
}
