import { DotBadge, type SemanticBadgeVariant } from "@/components/ui/badge";
import { PipelineActiveGlow, PIPELINE_ACTIVE_GLOW_SHADOW } from "@/components/dashboard/PipelineActiveGlow";
import { PipelineProgressBar } from "@/components/dashboard/PipelineProgressBar";
import { cn } from "@/lib/utils";
import type { PipelineStepStatus, PipelineStepView } from "@/lib/sampling/pipeline";

const STATUS_DOT: Record<PipelineStepStatus, { label: string; variant: SemanticBadgeVariant }> = {
  done: { label: "已完成", variant: "success" },
  processing: { label: "进行中", variant: "primary" },
  queued: { label: "等待中", variant: "gray" },
  failed: { label: "已失败", variant: "error" },
};

type PipelineStepCardProps = {
  step: PipelineStepView;
  compact?: boolean;
};

export function PipelineStepCard({ step, compact = false }: PipelineStepCardProps) {
  const statusDot = STATUS_DOT[step.status];
  const isActive = step.status === "processing";
  const isFailed = step.status === "failed";
  const isDone = step.status === "done";

  return (
    <div className={cn("relative", isActive && "pipeline-active-frame")}>
      <PipelineActiveGlow active={isActive} variant="card" />

      <article
        className={cn(
          "relative z-[1] rounded-xl border bg-muted-background transition-all duration-300",
          compact ? "p-3" : "p-4",
          !isActive && !compact && "shadow-sm",
          isActive && cn("border-primary/40", PIPELINE_ACTIVE_GLOW_SHADOW),
          isFailed && "border-error/35",
          isDone && "border-emerald-200/80 bg-emerald-50/60",
        )}
      >
        <div className="flex items-start gap-3">
          <div
            className={cn(
              "mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full font-mono text-xs font-semibold",
              isDone && "bg-emerald-500 text-primary-foreground",
              isActive && "bg-primary text-primary-foreground shadow-[0_0_12px_var(--primary-shadow-strong)]",
              step.status === "queued" && "bg-background text-muted-foreground",
              isFailed && "bg-error text-primary-foreground",
            )}
          >
            {String(step.index + 1).padStart(2, "0")}
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-sm font-semibold tracking-tight">{step.title}</h3>
              <DotBadge
                variant={statusDot.variant}
                className={cn(
                  "shrink-0 px-1.5 py-0.5 text-[10px] font-medium",
                  isActive && "[&>span:first-child]:animate-pulse",
                )}
              >
                {statusDot.label}
              </DotBadge>
            </div>
            {!compact ? (
              <p className="text-muted-foreground mt-1 text-xs leading-relaxed">{step.subtitle}</p>
            ) : null}

            <div className="mt-3 flex items-center gap-2">
              <PipelineProgressBar
                value={step.progress}
                active={isActive}
                failed={isFailed}
                done={isDone}
                trackClassName="min-w-0 flex-1"
                ariaLabel={`${step.title}进度`}
              />
              <span className="text-muted-foreground w-9 shrink-0 text-right text-[11px] tabular-nums">
                {step.progress}%
              </span>
            </div>
          </div>
        </div>
      </article>
    </div>
  );
}
