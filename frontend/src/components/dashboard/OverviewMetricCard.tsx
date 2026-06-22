import { CircleHelp } from "lucide-react";
import { useState, type ReactNode } from "react";

import { sentimentDotVariant } from "@/components/analysis/sentiment/SentimentValue";
import { DeltaBadge, DotBadge, TextBadge, type DeltaFormat, type SemanticBadgeVariant } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { sentimentDisplayLabel } from "@/lib/analysis/sentiment";
import { cn } from "@/lib/utils";

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

type OverviewCardLayoutProps = {
  title: string;
  description: string;
  value: ReactNode;
  progressFill: string;
  progressNow: number;
  progressAriaLabel: string;
  progressFillClassName?: string;
  bottomLeft?: ReactNode;
  bottomRight?: ReactNode;
  loading?: boolean;
  className?: string;
};

function OverviewCardLayout({
  title,
  description,
  value,
  progressFill,
  progressNow,
  progressAriaLabel,
  progressFillClassName = "bg-primary",
  bottomLeft,
  bottomRight,
  loading = false,
  className,
}: OverviewCardLayoutProps) {
  return (
    <div
      className={cn(
        "border-border relative flex min-h-[120px] min-w-0 w-full flex-col rounded-lg border bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04)]",
        className,
      )}
      aria-busy={loading}
    >
      <div className="flex h-5 items-center gap-1.5">
        <h3 className="text-sm font-medium text-foreground">{title}</h3>
        <MetricTitleInfo title={title} description={description} />
      </div>

      <div className="mt-3 flex h-8 items-center">{value}</div>

      <div className="mt-auto flex flex-col">
        <div
          className="bg-secondary mt-4 h-1 w-full overflow-hidden rounded-full"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progressNow}
          aria-label={progressAriaLabel}
        >
          {loading ? (
            <div className="bg-muted h-full w-full animate-pulse rounded-full" />
          ) : (
            <div
              className={cn("h-full rounded-full transition-all duration-500", progressFillClassName)}
              style={{ width: progressFill }}
            />
          )}
        </div>

        <div className="mt-2 flex h-5 items-stretch justify-between gap-2">
          <div className="flex min-w-0 flex-1 items-center">{bottomLeft}</div>
          <div className="flex shrink-0 items-center">{bottomRight}</div>
        </div>
      </div>
    </div>
  );
}

function sentimentTextClass(label: string): string {
  if (label === "正面") return "text-success";
  if (label === "负面") return "text-error";
  return "text-primary";
}

function sentimentBarClass(label: string): string {
  if (label === "正面") return "bg-success";
  if (label === "负面") return "bg-error";
  return "bg-primary";
}

/** 从 formatRate 文案（如 12.3%）解析进度条百分比 */
function progressPercentFromRateText(value: string): number {
  if (!value || value === "-") return 0;
  const parsed = Number.parseFloat(value.trim().replace(/%$/, ""));
  if (!Number.isFinite(parsed)) return 0;
  return Math.min(100, Math.max(0, parsed));
}

function isSentimentValue(value: OverviewMetricCardProps["value"]): value is number | null {
  return typeof value === "number" || value === null;
}

export type OverviewMetricCardBottomRight = {
  text: string;
  variant?: SemanticBadgeVariant;
};

export type OverviewMetricCardProps = {
  title: string;
  description: string;
  value: string | number | null;
  /** 后端 sentiment_label，仅情感卡片使用 */
  sentimentLabel?: string | null;
  deltaCurrent?: number | null;
  deltaPrevious?: number | null;
  deltaFormat?: DeltaFormat;
  bottomLeft?: string | null;
  bottomRight?: OverviewMetricCardBottomRight | null;
  loading?: boolean;
  className?: string;
};

function OverviewMetricDelta({
  deltaCurrent,
  deltaPrevious,
  deltaFormat = "percent",
}: Pick<OverviewMetricCardProps, "deltaCurrent" | "deltaPrevious" | "deltaFormat">) {
  return (
    <DeltaBadge
      current={deltaCurrent}
      previous={deltaPrevious}
      format={deltaFormat}
    />
  );
}

export function OverviewMetricCard({
  title,
  description,
  value,
  sentimentLabel,
  deltaCurrent,
  deltaPrevious,
  deltaFormat,
  bottomLeft,
  bottomRight,
  loading = false,
  className,
}: OverviewMetricCardProps) {
  if (isSentimentValue(value)) {
    const score = value;
    const label = sentimentDisplayLabel(sentimentLabel);
    const scoreText = score != null ? score.toFixed(1) : "-";
    const progressNow = score != null ? Math.min(100, Math.max(0, score)) : 0;
    const progressFill = `${progressNow}%`;

    return (
      <OverviewCardLayout
        title={title}
        description={description}
        loading={loading}
        className={className}
        progressFill={progressFill}
        progressNow={progressNow}
        progressAriaLabel={`情感得分 ${scoreText}`}
        progressFillClassName={sentimentBarClass(label)}
        value={
          loading ? (
            <div className="bg-muted h-8 w-16 max-w-full animate-pulse rounded-md" />
          ) : (
            <div className="flex min-w-0 items-center gap-2">
              <span
                className={cn("text-2xl font-bold leading-none tracking-tight", sentimentTextClass(label))}
              >
                {label}
              </span>
              <DotBadge variant={sentimentDotVariant(label)}>{scoreText}</DotBadge>
            </div>
          )
        }
        bottomLeft={
          loading ? (
            <div className="bg-muted h-full w-20 max-h-5 max-w-full animate-pulse rounded" />
          ) : bottomLeft ? (
            <p className="text-muted-foreground flex min-w-0 items-center gap-1.5 text-xs leading-none">
              <span className="truncate">{bottomLeft}</span>
            </p>
          ) : null
        }
        bottomRight={
          !loading && bottomRight ? (
            <TextBadge
              variant={bottomRight.variant ?? "gray"}
              className="h-5 shrink-0 rounded-md px-1.5 py-0 text-xs font-semibold leading-none"
            >
              {bottomRight.text}
            </TextBadge>
          ) : null
        }
      />
    );
  }

  const progressNow = progressPercentFromRateText(value);
  const progressFill = `${progressNow}%`;

  return (
    <OverviewCardLayout
      title={title}
      description={description}
      loading={loading}
      className={className}
      progressFill={progressFill}
      progressNow={progressNow}
      progressAriaLabel={`${title}进度`}
      value={
        loading ? (
          <div className="bg-muted h-8 w-16 max-w-full animate-pulse rounded-md" />
        ) : (
          <div className="flex min-w-0 items-center gap-2">
            <p className="text-2xl font-bold leading-none tracking-tight tabular-nums">{value}</p>
            <OverviewMetricDelta
              deltaCurrent={deltaCurrent}
              deltaPrevious={deltaPrevious}
              deltaFormat={deltaFormat}
            />
          </div>
        )
      }
      bottomLeft={
        loading ? (
          <div className="bg-muted h-full w-24 max-h-5 max-w-full animate-pulse rounded" />
        ) : bottomLeft ? (
          <p className="text-muted-foreground flex min-w-0 items-center gap-1.5 text-xs leading-none">
            <span className="truncate">{bottomLeft}</span>
          </p>
        ) : null
      }
      bottomRight={
        !loading && bottomRight ? (
          <TextBadge
            variant={bottomRight.variant ?? "gray"}
            className="h-5 shrink-0 rounded-md px-1.5 py-0 text-xs font-semibold leading-none"
          >
            {bottomRight.text}
          </TextBadge>
        ) : null
      }
    />
  );
}
