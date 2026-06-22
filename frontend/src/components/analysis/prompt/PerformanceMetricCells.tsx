import { CircleHelp } from "lucide-react";
import { useState, type SyntheticEvent } from "react";

import { SentimentValue } from "@/components/analysis/sentiment/SentimentValue";
import { DeltaBadgeSlot } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export function ColumnHelp({ label, description }: { label: string; description: string }) {
  const [open, setOpen] = useState(false);

  const toggleOpen = (event: SyntheticEvent) => {
    event.stopPropagation();
    event.preventDefault();
    setOpen((prev) => !prev);
  };

  return (
    <Tooltip open={open} onOpenChange={setOpen}>
      <TooltipTrigger asChild>
        <span
          role="button"
          tabIndex={0}
          className="text-muted-foreground hover:text-foreground inline-flex shrink-0 cursor-pointer rounded-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          aria-label={`了解${label}`}
          onClick={toggleOpen}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              toggleOpen(event);
            }
          }}
        >
          <CircleHelp className="size-4" aria-hidden />
        </span>
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
  text: string | null | undefined;
  /** 设置后 tooltip 仅展示截断后的内容 */
  tooltipMaxLength?: number;
}) {
  const tooltipText = text != null ?
    tooltipMaxLength != null && text.length > tooltipMaxLength
      ? `${text.slice(0, tooltipMaxLength).trimEnd()}…`
      : text : "—";

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="block w-full min-w-0 cursor-pointer truncate">{text || "—"}</span>
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

export function VisibilityMetricCell({
  value,
  delta,
}: {
  value: string;
  delta: string | null;
}) {
  return (
    <div className="inline-flex items-center gap-1.5 tabular-nums">
      <span>{value}</span>
      <DeltaBadgeSlot delta={delta} />
    </div>
  );
}

export function SentimentMetricCell({
  value,
  label,
}: {
  value: string;
  label?: string | null;
}) {
  return <SentimentValue value={value} label={label} />;
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
      <DeltaBadgeSlot delta={delta} />
    </div>
  );
}

export function EmptyMetricCell() {
  return <span className="text-foreground font-medium">—</span>;
}
