import { CircleHelp } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { isNeutralDelta } from "@/lib/analysis/format";
import { cn } from "@/lib/utils";

export function ColumnHelp({ label, description }: { label: string; description: string }) {
  const [open, setOpen] = useState(false);

  return (
    <Tooltip open={open} onOpenChange={setOpen}>
      <TooltipTrigger asChild>
        <button
          type="button"
          className="text-muted-foreground hover:text-foreground inline-flex shrink-0 rounded-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          aria-label={`了解${label}`}
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
        <p className="w-full text-wrap">{description}</p>
      </TooltipContent>
    </Tooltip>
  );
}

/** 提示词列正文：超出列宽省略，hover 展示全文 */
export function PromptTextCell({
  text,
  tooltipMaxLength,
}: {
  text: string;
  /** 设置后 tooltip 仅展示截断后的内容 */
  tooltipMaxLength?: number;
}) {
  const tooltipText =
    tooltipMaxLength != null && text.length > tooltipMaxLength
      ? `${text.slice(0, tooltipMaxLength).trimEnd()}…`
      : text;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="text-muted-foreground block w-full min-w-0 cursor-default truncate">{text}</span>
      </TooltipTrigger>
      <TooltipContent
        side="top"
        sideOffset={8}
        className={cn(
          "px-3 py-2.5 text-sm font-medium leading-relaxed text-left text-wrap",
          tooltipMaxLength != null ? "max-w-xs" : "max-w-[min(100vw-2rem,28rem)]",
        )}
      >
        <p className="w-full text-wrap">{tooltipText}</p>
      </TooltipContent>
    </Tooltip>
  );
}

function deltaVariant(delta: string): "green" | "red" | "muted" {
  if (delta.startsWith("+")) return "green";
  if (delta.startsWith("-")) return "red";
  return "muted";
}

export function PerformanceDeltaBadge({ delta }: { delta: string | null | undefined }) {
  if (!delta || isNeutralDelta(delta)) {
    return (
      <Badge variant="muted" className="rounded-md px-1.5 py-0 text-[11px] font-medium tabular-nums">
        -
      </Badge>
    );
  }

  return (
    <Badge
      variant={deltaVariant(delta)}
      className="rounded-md px-1.5 py-0 text-[11px] font-medium tabular-nums"
    >
      {delta}
    </Badge>
  );
}

export function VisibilityMetricCell({
  value,
  delta,
}: {
  value: string;
  delta: string | null;
}) {
  return (
    <div className="inline-flex items-center gap-1.5 tabular-nums">
      <span className="font-medium">{value}</span>
      <PerformanceDeltaBadge delta={delta} />
    </div>
  );
}

function sentimentDotClass(scoreText: string): string {
  if (scoreText === "正面") return "bg-emerald-500";
  if (scoreText === "负面") return "bg-red-500";
  if (scoreText === "中立") return "bg-amber-500";
  if (scoreText === "-") return "bg-muted-foreground/40";
  const score = Number.parseFloat(scoreText);
  if (!Number.isFinite(score)) return "bg-muted-foreground/40";
  if (score >= 55) return "bg-emerald-500";
  if (score < 45) return "bg-red-500";
  return "bg-amber-500";
}

export function SentimentMetricCell({
  value,
  delta,
}: {
  value: string;
  delta: string | null;
}) {
  return (
    <div className="inline-flex items-center gap-1.5 tabular-nums">
      <span
        className={cn("inline-block size-2 shrink-0 rounded-full", sentimentDotClass(value))}
        aria-hidden
      />
      <span className="font-medium">{value}</span>
      {delta ? <PerformanceDeltaBadge delta={delta} /> : null}
    </div>
  );
}

export function RankMetricCell({
  value,
  delta,
}: {
  value: string;
  delta: string | null;
}) {
  return (
    <div className="inline-flex items-center gap-1.5 tabular-nums">
      <span className="font-medium">{value}</span>
      {delta ? <PerformanceDeltaBadge delta={delta} /> : null}
    </div>
  );
}

export function EmptyMetricCell() {
  return <span className="text-muted-foreground">—</span>;
}
