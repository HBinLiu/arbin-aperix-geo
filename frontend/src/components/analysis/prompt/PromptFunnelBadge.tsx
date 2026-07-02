import { TextBadge, type SemanticBadgeVariant } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { funnelStageLabel, funnelStageTooltip } from "@/lib/analysis/promptTaxonomy";
import { cn } from "@/lib/utils";

type PromptFunnelBadgeProps = {
  stage: string | null | undefined;
  tooltipLabel?: string;
  className?: string;
};

function funnelBadgeVariant(label: string): SemanticBadgeVariant {
  if (label === "TOFU") return "info";
  if (label === "MOFU") return "warning";
  if (label === "BOFU") return "success";
  return "gray";
}

export function PromptFunnelBadge({ stage, tooltipLabel, className }: PromptFunnelBadgeProps) {
  const label = funnelStageLabel(stage);
  if (!label) return null;

  const tooltip = tooltipLabel?.trim() || funnelStageTooltip(stage);

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <TextBadge
          variant={funnelBadgeVariant(label)}
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
        {tooltip}
      </TooltipContent>
    </Tooltip>
  );
}
