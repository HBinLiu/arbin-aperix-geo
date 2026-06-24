import {
  buildPipelineStepViews,
  computeSamplingProcessedItems,
  estimatePipelineEtaSeconds,
  formatPipelineEta,
  pipelineOverallProgress,
  PIPELINE_STAGE_ORDER,
} from "@/lib/sampling/pipeline";
import { isPipelineComplete } from "@/lib/sampling/job-status";
import type { PipelineStepView } from "@/lib/sampling/pipeline";
import type { PipelineJobView, PipelineStatus } from "@/types";

function jobFromPipeline(pipeline: PipelineStatus | undefined): PipelineJobView | null {
  if (!pipeline?.latest_job) return null;
  const j = pipeline.latest_job;
  return {
    id: j.id,
    status: j.status as PipelineJobView["status"],
    total_items: j.total_items,
    failed_items: j.failed_items,
    error_message: j.error_message,
    started_at: j.started_at,
  };
}

export type DerivedPipelineState = {
  job: PipelineJobView | null;
  overallProgress: number;
  steps: PipelineStepView[];
  etaLabel: string;
  canShowMetrics: boolean;
  isRunning: boolean;
  isComplete: boolean;
  isFailed: boolean;
  currentStepIdx: number;
};

/** 路由 Gate / nav-lock 所需字段，避免 lib 依赖 hooks。 */
export type PipelineGateSnapshot = Pick<
  DerivedPipelineState,
  "isRunning" | "isComplete" | "isFailed"
> & {
  isLoading: boolean;
  job: DerivedPipelineState["job"];
};

export function derivePipelineState(pipeline: PipelineStatus | undefined): DerivedPipelineState {
  const job = jobFromPipeline(pipeline);
  const stage = pipeline?.stage ?? "verify";

  const totalItems = job?.total_items ?? 0;
  const processedItems = computeSamplingProcessedItems(pipeline, job);

  const isComplete = isPipelineComplete(pipeline);

  const isRunning =
    !isComplete && (stage === "dispatch" || stage === "clean" || stage === "analyze");
  const isFailed = job?.status === "failed" && !isComplete;

  const currentStepIdx = PIPELINE_STAGE_ORDER.indexOf(stage);

  const steps = buildPipelineStepViews({
    stage,
    job,
    pipeline,
    processedItems,
    totalItems,
    isComplete,
    isFailed,
  });

  const overallProgress = pipelineOverallProgress({
    pipeline,
    stage,
    processedItems,
    totalItems,
    isComplete,
  });

  const etaLabel = formatPipelineEta(
    estimatePipelineEtaSeconds({
      stage,
      job,
      pipeline,
      processedItems,
      totalItems,
      responseCount: pipeline?.response_count ?? 0,
      parsedCount: pipeline?.parsed_count ?? 0,
      isComplete,
    }),
  );

  return {
    job,
    overallProgress,
    steps,
    etaLabel,
    canShowMetrics: isComplete,
    isRunning,
    isComplete,
    isFailed,
    currentStepIdx,
  };
}
