import { TextBadge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { funnelStageLabel, funnelStageTooltip } from "@/lib/analysis/promptTaxonomy";
import { cn } from "@/lib/utils";

type PromptFunnelBadgeProps = {
  stage: string | null | undefined;
  className?: string;
};

export function PromptFunnelBadge({ stage, className }: PromptFunnelBadgeProps) {
  const label = funnelStageLabel(stage);
  if (!label) return null;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <TextBadge
          variant="info"
          className={cn("font-semibold", className)}
        >
          {label}
        </TextBadge>
      </TooltipTrigger>
      <TooltipContent
        side="top"
        sideOffset={8}
        className="px-2 py-1 text-sm font-medium leading-relaxed text-left text-wrap"
      >
        {funnelStageTooltip(stage)}
      </TooltipContent>
    </Tooltip>
  );
}
