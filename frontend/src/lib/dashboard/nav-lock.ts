import type { PipelineGateSnapshot } from "@/lib/sampling/pipeline-state";

export const SAMPLING_BLOCKED_MESSAGE = "请等待品牌分析任务完成";

/** 采样未完成时拦截洞察 / 运营路由（verify 阶段靠 job status 锁）。 */
export function isInsightOpsLocked(pipeline: PipelineGateSnapshot): boolean {
  if (pipeline.isLoading) return false;
  if (pipeline.isRunning) return true;
  const status = pipeline.job?.status;
  return status === "queued" || status === "running";
}
