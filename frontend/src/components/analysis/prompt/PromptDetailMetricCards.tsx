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
        <button
          type="button"
          className="text-muted-foreground hover:text-foreground inline-flex shrink-0 rounded-sm transition-colors"
          aria-label={`了解${label}`}
          onClick={() => setOpen((prev) => !prev)}
        >
          <CircleHelp className="size-4" aria-hidden />
        </button>
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
              "border-border flex min-h-[108px] flex-col rounded-lg border bg-white p-4 text-left shadow-[0_1px_2px_rgba(15,23,42,0.04)] transition-colors",
              active
                ? "border-orange-400 ring-1 ring-orange-400/40"
                : "hover:border-border/80 hover:bg-muted/20",
            )}
          >
            <div className="flex items-center gap-1.5">
              <span className="text-sm font-medium">{metric.label}</span>
              <MetricHelp label={metric.label} description={metric.description} />
            </div>
            {loading ? (
              <div className="bg-muted mt-4 h-8 w-20 animate-pulse rounded-md" />
            ) : (
              <p className="mt-3 text-2xl font-bold tracking-tight tabular-nums">
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
