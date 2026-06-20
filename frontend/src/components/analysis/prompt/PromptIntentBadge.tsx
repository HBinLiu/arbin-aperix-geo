import { TextBadge, type SemanticBadgeVariant } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { searchIntentBadgeLetter, searchIntentLabel } from "@/lib/analysis/promptTaxonomy";
import { cn } from "@/lib/utils";

type PromptIntentBadgeProps = {
  intent: string | null | undefined;
  className?: string;
};

function intentBadgeVariant(label: string): SemanticBadgeVariant {
  if (label === "I") return "info";
  if (label === "C") return "warning";
  if (label === "T") return "success";
  return "gray";
}

/** 提示词意图标记（I/C/T） */
export function PromptIntentBadge({ intent, className }: PromptIntentBadgeProps) {
  const label = searchIntentBadgeLetter(intent);
  if (!label) return null;

  const tooltip = searchIntentLabel(intent);

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <TextBadge
          variant={intentBadgeVariant(label)}
          className={cn(
            "inline-flex size-5 shrink-0 items-center justify-center rounded p-0 text-xs font-semibold",
            className,
          )}
        >
          {label}
        </TextBadge>
      </TooltipTrigger>
      <TooltipContent
        side="top"
        sideOffset={8}
        className="px-2 py-1 text-sm font-medium leading-relaxed text-left text-wrap"
      >
        {tooltip}
      </TooltipContent>
    </Tooltip>
  );
}
