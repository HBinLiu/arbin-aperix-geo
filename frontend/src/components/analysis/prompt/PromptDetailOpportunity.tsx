import { DotBadge, type SemanticBadgeVariant } from "@/components/ui/badge";
import {
  formatPromptGapRate,
  promptOpportunityPriorityLabel,
} from "@/lib/analysis/promptDetail";
import type { OpportunityPriority, PromptDetailOpportunityPayload } from "@/types";
import { cn } from "@/lib/utils";

const PRIORITY_VARIANT: Record<OpportunityPriority, SemanticBadgeVariant> = {
  high: "error",
  medium: "warning",
  low: "success",
};

const GAP_RING: Record<SemanticBadgeVariant, string> = {
  error: "border-error text-error",
  warning: "border-warning text-warning",
  success: "border-success text-success",
  gray: "border-border text-muted-foreground",
  primary: "border-primary text-primary",
  info: "border-info text-info",
};

type PromptDetailOpportunityProps = {
  opportunity: PromptDetailOpportunityPayload | null;
  loading?: boolean;
};

function GapCard({
  title,
  gapRate,
  gapPriority,
  loading,
}: {
  title: string;
  gapRate: number;
  gapPriority: OpportunityPriority;
  loading?: boolean;
}) {
  const variant = PRIORITY_VARIANT[gapPriority];

  return (
    <div className="border-border flex flex-1 flex-col rounded-lg border bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
      <h4 className="text-sm font-semibold">{title}</h4>
      <div className="mt-5 flex flex-wrap items-center gap-4">
        {loading ? (
          <div className="bg-muted h-16 w-28 animate-pulse rounded-3xl" />
        ) : (
          <div
            className={cn(
              "flex min-w-28 items-center justify-center rounded-3xl border-[3px] px-4 py-2.5 text-center text-sm font-bold leading-tight",
              GAP_RING[variant],
            )}
          >
            {formatPromptGapRate(gapRate)}
          </div>
        )}
        {loading ? (
          <span className="text-sm font-medium">…</span>
        ) : (
          <DotBadge variant={variant} className="px-2 py-0.5 text-sm">
            {promptOpportunityPriorityLabel(gapPriority)}
          </DotBadge>
        )}
      </div>
    </div>
  );
}

/** 提示词详情 · 机会摘要（品牌差距 / 来源差距） */
export function PromptDetailOpportunity({
  opportunity,
  loading = false,
}: PromptDetailOpportunityProps) {
  return (
    <section className="border-border overflow-hidden rounded-lg border bg-white">
      <div className="border-border border-b bg-muted px-5 py-3">
        <h3 className="text-base font-semibold">机会</h3>
        <p className="text-muted-foreground mt-1 text-sm font-medium leading-relaxed">
          量化当前品牌相对其他竞品的 AI 提及与来源引用差距，识别高潜力增长空间。
        </p>
      </div>
      <div className="flex flex-col gap-4 p-5 lg:flex-row">
        <GapCard
          title="品牌差距"
          gapRate={opportunity?.brand_gap_rate ?? 0}
          gapPriority={opportunity?.brand_gap_priority ?? "low"}
          loading={loading}
        />
        <GapCard
          title="来源差距"
          gapRate={opportunity?.source_gap_rate ?? 0}
          gapPriority={opportunity?.source_gap_priority ?? "low"}
          loading={loading}
        />
      </div>
    </section>
  );
}
