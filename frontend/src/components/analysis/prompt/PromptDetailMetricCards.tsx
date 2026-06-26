import { CircleHelp } from "lucide-react";
import { useState } from "react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import {
  PROMPT_DETAIL_METRICS,
  promptDetailMetric,
  type PromptDetailMetricId,
} from "@/lib/analysis/promptDetail";
import { cn } from "@/lib/utils";

type PromptDetailMetricCardsProps = {
  activeMetricId: PromptDetailMetricId;
  onMetricChange: (metricId: PromptDetailMetricId) => void;
  values: Partial<Record<PromptDetailMetricId, string>>;
  loading?: boolean;
};

function MetricHelp({ label, description }: { label: string; description: string }) {
  const [open, setOpen] = useState(false);

  return (
    <Tooltip open={open} onOpenChange={setOpen}>
      <TooltipTrigger asChild>
        <span
          role="button"
          tabIndex={0}
          className="text-muted-foreground hover:text-foreground inline-flex shrink-0 rounded-sm transition-colors"
          aria-label={`了解${label}`}
          onClick={(event) => {
            event.stopPropagation();
            setOpen((prev) => !prev);
          }}
          onKeyDown={(event) => {
            if (event.key !== "Enter" && event.key !== " ") return;
            event.preventDefault();
            event.stopPropagation();
            setOpen((prev) => !prev);
          }}
        >
          <CircleHelp className="size-4" aria-hidden />
        </span>
      </TooltipTrigger>
      <TooltipContent
        side="top"
        sideOffset={8}
        className="max-w-[280px] px-3 py-2.5 text-sm font-medium leading-relaxed text-left text-wrap"
      >
        {description}
      </TooltipContent>
    </Tooltip>
  );
}

/** 提示词详情 · 指标摘要卡片（可切换图表） */
export function PromptDetailMetricCards({
  activeMetricId,
  onMetricChange,
  values,
  loading = false,
}: PromptDetailMetricCardsProps) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {PROMPT_DETAIL_METRICS.map((metric) => {
        const active = metric.id === activeMetricId;
        return (
          <button
            key={metric.id}
            type="button"
            aria-pressed={active}
            onClick={() => onMetricChange(metric.id)}
            className={cn(
              "border-border flex flex-col rounded-lg border bg-muted-background px-6 py-4 text-left transition-colors",
              active
                ? "border-primary shadow-[8px_10px_16px_-8px_rgba(15,23,42,0.12)]"
                : "hover:border-primary/60 hover:shadow-[8px_10px_16px_-8px_rgba(15,23,42,0.12)]",
            )}
          >
            <div className="flex items-center gap-1.5">
              <span className="text-sm text-muted-foreground font-medium">{metric.label}</span>
              <MetricHelp label={metric.label} description={metric.description} />
            </div>
            {loading ? (
              <div className="bg-background mt-4 h-8 w-20 animate-pulse rounded-md" />
            ) : (
              <p className="mt-4 text-2xl font-bold tracking-tight tabular-nums">
                {values[metric.id] ?? "—"}
              </p>
            )}
          </button>
        );
      })}
    </div>
  );
}

export function promptDetailMetricCardValues(
  summary: {
    visibility_rate: number | null;
    average_rank: number | null;
    citation_rate: number | null;
  } | null | undefined,
): Partial<Record<PromptDetailMetricId, string>> {
  if (!summary) return {};
  return {
    visibility: promptDetailMetric("visibility").formatValue(summary.visibility_rate),
    averageRank: promptDetailMetric("averageRank").formatValue(summary.average_rank),
    citation: promptDetailMetric("citation").formatValue(summary.citation_rate),
  };
}
