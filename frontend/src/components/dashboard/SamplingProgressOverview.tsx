import { Link } from "react-router-dom";
import { ArrowRight, CircleX, Loader2 } from "lucide-react";
import { useMutation } from "@tanstack/react-query";

import { retrySamplingJob } from "@/api/sampling";
import { formatApiError } from "@/api/client";
import { PipelineProgressRing } from "@/components/dashboard/PipelineProgressRing";
import { PipelineStepCard } from "@/components/dashboard/PipelineStepCard";
import { Button } from "@/components/ui/button";
import type { SubjectPipelineState } from "@/hooks/useSubjectPipeline";
import { dashboardNavToPath } from "@/lib/dashboard";
import {
  formatPipelinePhaseHeadline,
  reconnectPipelineStream,
} from "@/lib/sampling";
import { toast } from "@/lib/toast";

type SamplingProgressOverviewProps = {
  subjectId: string;
  pipeline: SubjectPipelineState;
};

export function SamplingProgressOverview({
  subjectId,
  pipeline,
}: SamplingProgressOverviewProps) {
  const {
    steps,
    currentStepIdx,
    etaLabel,
    isFailed,
    job,
    isLoading,
    overallProgress,
    streamError,
  } = pipeline;

  const retryMutation = useMutation({
    mutationFn: () => retrySamplingJob(subjectId),
    onSuccess: () => {
      reconnectPipelineStream(subjectId);
      toast.info("已重新提交采样任务，请稍候。");
    },
    onError: (error) => {
      toast.error(formatApiError(error, "重试失败，请联系管理员。"));
    },
  });

  if (isLoading) {
    return (
      <div className="flex min-h-[24rem] items-center justify-center px-6 py-12">
        <Loader2 className="text-primary size-8 animate-spin" aria-hidden />
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      <div className="border-primary/15 bg-primary/5 border-b px-4 py-2.5 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-primary text-xs font-medium">
            系统初始化：{formatPipelinePhaseHeadline(steps, currentStepIdx)}
          </p>
          {streamError && !isFailed ? (
            <button
              type="button"
              className="text-muted-foreground hover:text-foreground text-xs underline-offset-2 hover:underline"
              onClick={() => reconnectPipelineStream(subjectId)}
            >
              进度连接中断，点击重试
            </button>
          ) : null}
        </div>
      </div>

      <div className="grid gap-8 px-4 py-8 sm:px-6 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] lg:items-stretch lg:py-10">
        <section className="flex min-h-[min(24rem,100%)] flex-col items-center justify-center text-center lg:min-h-full">
          <PipelineProgressRing value={overallProgress} label="总体进度" />
          {isFailed ? (
            <>
              <h2
                className="text-destructive mt-6 flex items-center justify-center gap-2 text-xl font-semibold tracking-tight sm:text-2xl"
              >
                <CircleX className="size-6 shrink-0 sm:size-7" aria-hidden />
                品牌分析失败
              </h2>
              <p className="text-muted-foreground mx-auto mt-3 max-w-md text-sm leading-relaxed">
                {job?.error_message?.trim() ||
                  "任务未能完成，请尝试重试；若仍失败请联系管理员。"}
              </p>
              <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={retryMutation.isPending}
                  onClick={() => retryMutation.mutate()}
                >
                  {retryMutation.isPending ? "重试中…" : "重试任务"}
                </Button>
                <Button type="button" size="sm" variant="brandout" asChild>
                  <Link to="/about">联系管理员</Link>
                </Button>
              </div>
            </>
          ) : (
            <>
              <h2 className="mt-6 text-2xl font-semibold tracking-tight sm:text-3xl">
                我们正在分析您的品牌
              </h2>
              <p className="text-muted-foreground mx-auto mt-3 max-w-md text-sm leading-relaxed">
                预计{etaLabel}完成，当数据完全准备就绪后，我们将通知您。
              </p>
            </>
          )}
        </section>

        <section className="flex flex-col gap-3">
          {steps.map((step) => (
            <PipelineStepCard key={step.id} step={step} />
          ))}

          <div className="border-border/80 mt-1 flex flex-col gap-3 rounded-xl border bg-white p-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-muted-foreground text-xs">预计完成时间：{etaLabel}。</p>
            <Button variant="default" size="sm" className="rounded-lg px-4" asChild>
              <Link to={dashboardNavToPath("brand")}>
                查看品牌设置
                <ArrowRight className="size-3.5" aria-hidden />
              </Link>
            </Button>
          </div>
        </section>
      </div>
    </div>
  );
}
