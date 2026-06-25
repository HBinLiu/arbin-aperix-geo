import { formatPipelinePhaseHeadline } from "@/lib/sampling/pipeline";
import type { SubjectPipelineState } from "@/hooks/useSubjectPipeline";
import { PipelineActiveGlow, PIPELINE_ACTIVE_GLOW_SHADOW } from "@/components/dashboard/PipelineActiveGlow";
import { PipelineProgressBar } from "@/components/dashboard/PipelineProgressBar";
import { cn } from "@/lib/utils";

type SamplingProgressSidebarProps = {
  pipeline: SubjectPipelineState;
};

export function SamplingProgressSidebar({ pipeline }: SamplingProgressSidebarProps) {
  const {
    steps,
    currentStepIdx,
    etaLabel,
    isFailed,
    isComplete,
    overallProgress,
  } = pipeline;

  if (isComplete) return null;

  const isActive = !isFailed;

  return (
    <div className={cn("relative shrink-0", isActive && "pipeline-active-frame")}>
      <PipelineActiveGlow active={isActive} variant="sidebar" />

      <div
        className={cn(
          "border-border/80 relative z-[1] rounded-lg border bg-white p-3 transition-all duration-300",
          isActive && cn("border-primary/40", PIPELINE_ACTIVE_GLOW_SHADOW),
          isFailed && "border-destructive/35",
          !isActive && "shadow-[8px_10px_24px_-10px_rgba(15,23,42,0.12)]",
        )}
      >
        <div className="flex items-center justify-between gap-2">
          <p className="text-foreground text-sm font-medium">
            {isFailed ? "采样任务失败" : "正在生成报告…"}
          </p>
          <span className="text-primary text-xs font-semibold tabular-nums">
            {overallProgress}%
          </span>
        </div>

        <PipelineProgressBar
          value={overallProgress}
          active={isActive}
          failed={isFailed}
          heightClass="h-full"
          trackClassName="mt-2 h-1 w-full"
          fillClassName="h-full"
          ariaLabel="采样总进度"
        />

        <p className="text-muted-foreground mt-2 text-xs leading-relaxed">
          {isFailed
            ? "请在概述页重试或联系管理员。"
            : `${formatPipelinePhaseHeadline(steps, currentStepIdx)}，预计 ${etaLabel}。`}
        </p>
      </div>
    </div>
  );
}
