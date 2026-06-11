import { cn } from "@/lib/utils";
import { funnelStageLabel } from "@/lib/analysis/promptTaxonomy";

type PromptFunnelBadgeProps = {
  stage: string;
  className?: string;
};

export function PromptFunnelBadge({ stage, className }: PromptFunnelBadgeProps) {
  const label = funnelStageLabel(stage);
  if (!label || label === "—") return null;

  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center rounded bg-sky-100 px-2 py-0.5 text-[11px] font-semibold text-sky-800",
        className,
      )}
      title={`营销漏斗：${label}`}
    >
      {label}
    </span>
  );
}
