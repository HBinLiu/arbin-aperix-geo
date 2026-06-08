import type { LucideIcon } from "lucide-react";

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
  className?: string;
};

const PRIORITY_META: { id: OpportunityPriority; label: string; dotClass: string }[] = [
  { id: "high", label: "高", dotClass: "bg-red-500" },
  { id: "medium", label: "中", dotClass: "bg-amber-500" },
  { id: "low", label: "低", dotClass: "bg-emerald-500" },
];

/** 诊断维度摘要卡 */
export function DiagnosisDimensionCard({
  title,
  description,
  icon: Icon,
  healthScore,
  priorityCounts,
  active = false,
  loading = false,
  className,
}: DiagnosisDimensionCardProps) {
  return (
    <div
      className={cn(
        "border-border flex min-h-[220px] flex-col rounded-lg border bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04)]",
        active && "border-primary/30 bg-accent/30",
        className,
      )}
      aria-busy={loading}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <div
            className={cn(
              "flex size-10 shrink-0 items-center justify-center rounded-lg",
              active ? "bg-primary text-primary-foreground" : "bg-muted text-foreground",
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
        </div>
        <div className="shrink-0 text-right">
          <p className="text-muted-foreground text-xs">健康评分</p>
          {loading ? (
            <div className="bg-muted mt-1 h-7 w-16 animate-pulse rounded" />
          ) : (
            <p className={cn("mt-0.5 text-xl font-bold tabular-nums", active ? "text-primary" : "text-foreground")}>
              {healthScore.toFixed(1)}
              <span className="text-muted-foreground text-sm font-medium"> / 100</span>
            </p>
          )}
        </div>
      </div>

      <div className="mt-auto flex flex-wrap items-center gap-3 pt-5">
        <span className="text-muted-foreground text-xs">行动优先级</span>
        {PRIORITY_META.map((item) => (
          <span key={item.id} className="inline-flex items-center gap-1 text-xs font-medium">
            <span className={cn("inline-block size-2 rounded-full", item.dotClass)} aria-hidden />
            {item.label}
            <span className="text-muted-foreground tabular-nums">x{priorityCounts[item.id]}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
