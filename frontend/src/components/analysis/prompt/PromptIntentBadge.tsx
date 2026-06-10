import { cn } from "@/lib/utils";

type PromptIntentBadgeProps = {
  intent: string;
  className?: string;
};

/** 提示词意图标记（如 T = 交易型） */
export function PromptIntentBadge({ intent, className }: PromptIntentBadgeProps) {
  const label = intent.trim().slice(0, 1).toUpperCase();
  if (!label) return null;

  return (
    <span
      className={cn(
        "inline-flex size-5 shrink-0 items-center justify-center rounded bg-emerald-500 text-[11px] font-bold text-white",
        className,
      )}
      title={`意图：${intent}`}
    >
      {label}
    </span>
  );
}
