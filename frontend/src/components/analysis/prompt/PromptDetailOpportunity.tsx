import {
  formatPromptGapRate,
  promptOpportunityPriorityLabel,
  type PromptOpportunitySummary,
} from "@/lib/analysis/promptDetail";
import type { OpportunityPriority } from "@/types";
import { cn } from "@/lib/utils";

const PRIORITY_DOT: Record<OpportunityPriority, string> = {
  high: "bg-red-500",
  medium: "bg-amber-500",
  low: "bg-emerald-500",
};

const GAP_RING: Record<OpportunityPriority, string> = {
  high: "border-red-400 text-red-500",
  medium: "border-amber-400 text-amber-600",
  low: "border-emerald-400 text-emerald-600",
};

type PromptDetailOpportunityProps = {
  opportunity: PromptOpportunitySummary | null;
  loading?: boolean;
};

function GapCard({
  title,
  gapRate,
  priority,
  loading,
}: {
  title: string;
  gapRate: number;
  priority: OpportunityPriority;
  loading?: boolean;
}) {
  return (
    <div className="border-border flex flex-1 flex-col rounded-lg border bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
      <h4 className="text-sm font-semibold">{title}</h4>
      <div className="mt-5 flex flex-wrap items-center gap-5">
        {loading ? (
          <div className="bg-muted h-16 w-28 animate-pulse rounded-3xl" />
        ) : (
          <div
            className={cn(
              "flex min-w-28 items-center justify-center rounded-3xl border-[3px] px-4 py-3 text-center text-sm font-bold leading-tight",
              GAP_RING[priority],
            )}
          >
            {formatPromptGapRate(gapRate)}
          </div>
        )}
        <div className="inline-flex items-center gap-1.5 text-sm font-medium">
          <span
            className={cn("inline-block size-2 rounded-full", PRIORITY_DOT[priority])}
            aria-hidden
          />
          {loading ? "…" : promptOpportunityPriorityLabel(priority)}
        </div>
      </div>
    </div>
  );
}

/** 提示词详情 · 机会摘要（品牌差距 / 来源差距） */
export function PromptDetailOpportunity({
  opportunity,
  loading = false,
}: PromptDetailOpportunityProps) {
  const priority = opportunity?.priority ?? "low";

  return (
    <section className="border-border overflow-hidden rounded-lg border bg-white">
      <div className="border-border border-b px-5 py-4">
        <h3 className="text-base font-semibold">机会</h3>
        <p className="text-muted-foreground mt-1 text-sm leading-relaxed">
          量化品牌在该提示词下错失的 AI 提及与引用机会，识别高潜力增长空间。
        </p>
      </div>
      <div className="flex flex-col gap-4 p-5 lg:flex-row">
        <GapCard
          title="品牌差距"
          gapRate={opportunity?.brandGapRate ?? 0}
          priority={priority}
          loading={loading}
        />
        <GapCard
          title="来源差距"
          gapRate={opportunity?.sourceGapRate ?? 0}
          priority={priority}
          loading={loading}
        />
      </div>
    </section>
  );
}
