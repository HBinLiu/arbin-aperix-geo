import { cn } from "@/lib/utils";
import { searchIntentBadgeLetter, searchIntentLabel } from "@/lib/analysis/promptTaxonomy";

type PromptIntentBadgeProps = {
  intent: string;
  className?: string;
};

/** 提示词意图标记（I/C/T） */
export function PromptIntentBadge({ intent, className }: PromptIntentBadgeProps) {
  const label = searchIntentBadgeLetter(intent);
  if (!label || label === "?") return null;

  return (
    <span
      className={cn(
        "inline-flex size-5 shrink-0 items-center justify-center rounded bg-emerald-500 text-[11px] font-bold text-white",
        className,
      )}
      title={`意图：${searchIntentLabel(intent)}`}
    >
      {label}
    </span>
  );
}
