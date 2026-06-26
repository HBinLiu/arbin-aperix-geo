import type { LucideIcon } from "lucide-react";

import { TextBadge, type SemanticBadgeVariant } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { OpportunityPriority } from "@/types";

type PriorityCounts = Record<OpportunityPriority, number>;

type DiagnosisDimensionCardProps = {
  title: string;
  description: string;
  icon: LucideIcon;
  healthScore: number;
  priorityCounts: PriorityCounts;
  active?: boolean;
  loading?: boolean;
  /** 嵌入合并面板时使用：无独立边框，均分宽度 */
  embedded?: boolean;
  className?: string;
};

const PRIORITY_VARIANT: Record<OpportunityPriority, SemanticBadgeVariant> = {
  high: "error",
  medium: "warning",
  low: "success",
};

const PRIORITY_META: { id: OpportunityPriority; label: string }[] = [
  { id: "high", label: "高" },
  { id: "medium", label: "中" },
  { id: "low", label: "低" },
];

/** 与综合诊断状态分段一致：≥60 良好，≥40 待提升，否则严重 */
function healthScoreTone(score: number): "success" | "warning" | "error" {
  if (score >= 60) return "success";
  if (score >= 40) return "warning";
  return "error";
}

const HEALTH_SCORE_GRADIENT_CLASS: Record<"success" | "warning" | "error", string> = {
  success: "bg-gradient-to-b from-success/20 via-success/8 to-surface",
  warning: "bg-gradient-to-b from-warning/20 via-warning/8 to-surface",
  error: "bg-gradient-to-b from-error/20 via-error/8 to-surface",
};

const HEALTH_SCORE_TEXT_CLASS: Record<"success" | "warning" | "error", string> = {
  success: "text-success",
  warning: "text-warning",
  error: "text-error",
};

const HEALTH_SCORE_PROGRESS_CLASS: Record<"success" | "warning" | "error", string> = {
  success: "bg-success",
  warning: "bg-warning",
  error: "bg-error",
};

/** 诊断维度摘要卡：上（标题）· 中（健康评分）· 下（行动优先级） */
export function DiagnosisDimensionCard({
  title,
  description,
  icon: Icon,
  healthScore,
  priorityCounts,
  active = false,
  loading = false,
  embedded = false,
  className,
}: DiagnosisDimensionCardProps) {
  const progressNow = Math.min(100, Math.max(0, healthScore));
  const visiblePriorities = PRIORITY_META.filter((item) => priorityCounts[item.id] > 0);
  const scoreTone = healthScoreTone(healthScore);

  return (
    <div
      className={cn(
        "flex h-full min-h-[220px] flex-col",
        embedded ? "min-w-0 flex-1" : "rounded-lg border border-border/60 shadow-[0_1px_2px_rgba(15,23,42,0.04)]",
        loading ? "bg-muted-background" : HEALTH_SCORE_GRADIENT_CLASS[scoreTone],
        className,
      )}
      aria-busy={loading}
    >
      {/* 上：维度标题与说明 */}
      <section className="flex min-h-0 flex-1 items-start gap-3 px-5 pt-5 pb-4">
        <div
          className={cn(
            "flex size-10 shrink-0 items-center justify-center rounded-lg",
            active ? "bg-primary text-primary-foreground" : "bg-muted-background/80 text-foreground shadow-sm",
          )}
        >
          <Icon className="size-5" aria-hidden />
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold">{title}</h3>
            {active ? <span className="bg-primary inline-block size-2 rounded-full" aria-hidden /> : null}
          </div>
          <p className="text-muted-foreground mt-1 text-xs leading-relaxed">{description}</p>
        </div>
      </section>

      {/* 中：健康评分 */}
      <section className="flex shrink-0 flex-col justify-end px-5 py-4">
        <div className="mb-2 flex h-4 items-center justify-between gap-2">
          <p className="text-muted-foreground text-xs">健康评分</p>
          {loading ? (
            <div className="bg-background h-4 w-14 animate-pulse rounded" />
          ) : (
            <p className={cn("text-xs font-semibold tabular-nums", HEALTH_SCORE_TEXT_CLASS[scoreTone])}>
              {healthScore.toFixed(1)}
              <span className="text-muted-foreground font-medium"> / 100</span>
            </p>
          )}
        </div>

        <div
          className="bg-background h-1 w-full overflow-hidden rounded-full"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={loading ? 0 : progressNow}
          aria-label={`${title}健康评分 ${loading ? "加载中" : healthScore.toFixed(1)}`}
        >
          {loading ? (
            <div className="bg-background h-full w-full animate-pulse rounded-full" />
          ) : (
            <div
              className={cn("h-full rounded-full transition-all duration-500", HEALTH_SCORE_PROGRESS_CLASS[scoreTone])}
              style={{ width: `${progressNow}%` }}
            />
          )}
        </div>
      </section>

      {/* 下：行动优先级 */}
      <section className="flex min-h-9 shrink-0 flex-wrap items-center gap-2 px-5 pt-4 pb-5">
        <span className="text-muted-foreground shrink-0 text-xs">行动优先级</span>
        {loading ? (
          <div className="bg-background h-5 w-24 animate-pulse rounded-full" />
        ) : (
          visiblePriorities.map((item) => (
            <TextBadge
              key={item.id}
              variant={PRIORITY_VARIANT[item.id]}
              className="px-2 py-0.5 text-xs font-semibold tabular-nums"
            >
              {item.label} x{priorityCounts[item.id]}
            </TextBadge>
          ))
        )}
      </section>
    </div>
  );
}
