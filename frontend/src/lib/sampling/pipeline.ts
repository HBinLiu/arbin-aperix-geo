import type { PipelineJobView, PipelineStatus } from "@/types";

export const PIPELINE_STAGE_ORDER = ["verify", "dispatch", "clean", "analyze"] as const;

export type PipelineStageId = (typeof PIPELINE_STAGE_ORDER)[number];

export type PipelineStepStatus = "done" | "processing" | "queued" | "failed";

export type PipelineStepView = {
  id: PipelineStageId;
  index: number;
  title: string;
  subtitle: string;
  status: PipelineStepStatus;
  progress: number;
};

export const PIPELINE_STEP_COPY: Record<
  PipelineStageId,
  { title: string; subtitle: string }
> = {
  verify: {
    title: "品牌信息验证",
    subtitle: "您的品牌信息已经成功验证。",
  },
  dispatch: {
    title: "大模型任务调度",
    subtitle: "扫描全局节点并收集原始模型数据。",
  },
  clean: {
    title: "语义清洗降噪",
    subtitle: "识别语义并清理噪音提取有效信息。",
  },
  analyze: {
    title: "声量聚合诊断",
    subtitle: "生成可视化图表和最终品牌策略。",
  },
};

/** Overview 时间预估固定按 Setup 所选提示词 × 默认单平台。 */
export const OVERVIEW_ETA_PLATFORM_COUNT = 1;

const DISPATCH_BATCH_SIZE = 10;
/** 单批并发采样的典型墙钟耗时（与后端 sampling_max_inflight 对齐）。 */
const DISPATCH_BATCH_SECONDS = 100;
const CLEAN_ITEM_SECONDS = 4;
const ANALYZE_SECONDS = 20;
const MIN_ETA_SECONDS = 60;
const MAX_ETA_SECONDS = 35 * 60;

function clampEta(seconds: number): number {
  return Math.min(MAX_ETA_SECONDS, Math.max(MIN_ETA_SECONDS, Math.round(seconds)));
}

/** Setup 提示词数 × 平台数 → 采样条数。 */
export function plannedSamplingItems(
  promptCount: number,
  platformCount = OVERVIEW_ETA_PLATFORM_COUNT,
): number {
  return Math.max(0, promptCount) * platformCount;
}

/** 整次采样任务的墙钟预算（秒）。 */
export function estimateSamplingBudgetFromItems(itemCount: number): number {
  const items = Math.max(0, itemCount);
  if (items <= 0) return clampEta(8 * 60);
  const batches = Math.ceil(items / DISPATCH_BATCH_SIZE);
  return clampEta(
    batches * DISPATCH_BATCH_SECONDS + items * CLEAN_ITEM_SECONDS + ANALYZE_SECONDS,
  );
}

/** 整次采样任务的墙钟预算（秒）。 */
export function estimateSamplingBudgetSeconds(
  promptCount: number,
  platformCount = OVERVIEW_ETA_PLATFORM_COUNT,
): number {
  return estimateSamplingBudgetFromItems(plannedSamplingItems(promptCount, platformCount));
}

const STAGE_WEIGHTS: Record<PipelineStageId, number> = {
  verify: 8,
  dispatch: 52,
  clean: 35,
  analyze: 5,
};

/** 0–100，用于 ETA 外推（与概述页总进度一致）。 */
export function pipelineOverallProgress(input: {
  pipeline: PipelineStatus | undefined;
  stage: PipelineStageId;
  processedItems: number;
  totalItems: number;
  isComplete: boolean;
}): number {
  if (input.isComplete) return 100;

  const stageIdx = PIPELINE_STAGE_ORDER.indexOf(input.stage);
  const responseCount = input.pipeline?.response_count ?? 0;
  const parsedCount = input.pipeline?.parsed_count ?? 0;

  const stageProgressAt = (id: PipelineStageId): number => {
    switch (id) {
      case "verify":
        return input.pipeline?.latest_job ? 100 : 0;
      case "dispatch":
        return dispatchProgress(input.processedItems, input.totalItems);
      case "clean":
        return cleanStageProgress(input.pipeline, input.totalItems);
      case "analyze":
        if (parsedCount > 0 && responseCount > 0) {
          return cleanProgress(parsedCount, responseCount);
        }
        return 0;
    }
  };

  let sum = 0;
  for (let i = 0; i < PIPELINE_STAGE_ORDER.length; i++) {
    const weight = STAGE_WEIGHTS[PIPELINE_STAGE_ORDER[i]];
    if (i < stageIdx) {
      sum += weight;
    } else if (i === stageIdx) {
      sum += weight * (stageProgressAt(PIPELINE_STAGE_ORDER[i]) / 100);
    }
  }

  return Math.min(99, Math.round(sum));
}

/**
 * 调度阶段已推进条数：非 pending 的 response（含 llm/crawl/parse 中与 success/failed）。
 * response_count 仅统计 success，单独用它会导致 dispatch 进度长期为 0。
 */
export function computeSamplingProcessedItems(
  pipeline: PipelineStatus | undefined,
  job: PipelineJobView | null,
): number {
  const total =
    job?.total_items ?? pipeline?.latest_job?.total_items ?? 0;
  if (!pipeline || total <= 0) {
    const failed = job?.failed_items ?? pipeline?.latest_job?.failed_items ?? 0;
    return (pipeline?.response_count ?? 0) + failed;
  }
  const pending = pipeline.llm_pending_count ?? 0;
  return Math.min(total, Math.max(0, total - pending));
}

function stageRemainingSeconds(input: {
  stage: PipelineStageId;
  processedItems: number;
  totalItems: number;
  responseCount: number;
  parsedCount: number;
}): number {
  const dispatchRemaining = Math.max(0, input.totalItems - input.processedItems);
  const cleanRemaining = Math.max(0, input.responseCount - input.parsedCount);
  const dispatchBatches = Math.ceil(dispatchRemaining / DISPATCH_BATCH_SIZE);

  switch (input.stage) {
    case "verify":
      return 45;
    case "dispatch":
      return (
        dispatchBatches * DISPATCH_BATCH_SECONDS + cleanRemaining * CLEAN_ITEM_SECONDS
      );
    case "clean":
      return cleanRemaining * CLEAN_ITEM_SECONDS + ANALYZE_SECONDS;
    case "analyze":
      return ANALYZE_SECONDS;
  }
}

export function estimatePipelineEtaSeconds(input: {
  stage: PipelineStageId;
  job: PipelineJobView | null;
  processedItems: number;
  totalItems: number;
  responseCount: number;
  parsedCount: number;
  isComplete: boolean;
  pipeline?: PipelineStatus;
}): number | null {
  if (input.isComplete) return 0;

  const overallProgress = pipelineOverallProgress({
    pipeline: input.pipeline,
    stage: input.stage,
    processedItems: input.processedItems,
    totalItems: input.totalItems,
    isComplete: input.isComplete,
  });

  if (input.totalItems > 0) {
    const budget = estimateSamplingBudgetFromItems(input.totalItems);
    if (overallProgress >= 98) return MIN_ETA_SECONDS;
    const remaining = budget * (1 - overallProgress / 100);
    return clampEta(remaining);
  }

  const heuristic = stageRemainingSeconds(input);

  const startedAt = input.job?.started_at;
  if (startedAt && overallProgress >= 10) {
    const elapsedSeconds = Math.max(
      1,
      (Date.now() - new Date(startedAt).getTime()) / 1000,
    );
    const extrapolated =
      (elapsedSeconds * (100 - overallProgress)) / Math.max(overallProgress, 1);
    if (Number.isFinite(extrapolated) && extrapolated > 0) {
      const trust = Math.min(1, (overallProgress - 10) / 35);
      const blended = heuristic * (1 - trust) + extrapolated * trust;
      return clampEta(blended);
    }
  }

  return clampEta(heuristic);
}

function clampPercent(value: number): number {
  return Math.min(100, Math.max(0, Math.round(value)));
}

function dispatchProgress(processedItems: number, totalItems: number): number {
  if (totalItems <= 0) return 0;
  return clampPercent((processedItems / totalItems) * 100);
}

function cleanProgress(parsedCount: number, responseCount: number): number {
  if (responseCount <= 0) return 0;
  return clampPercent((parsedCount / responseCount) * 100);
}

/** Clean 阶段进度：有 success 时用 parsed 比；否则按 llm/crawl 在途加权估算。 */
export function cleanStageProgress(
  pipeline: PipelineStatus | undefined,
  totalItems: number,
): number {
  if (totalItems <= 0 || !pipeline) return 0;

  const parsed = pipeline.parsed_count ?? 0;
  const success = pipeline.response_count ?? 0;
  if (success > 0) {
    return cleanProgress(parsed, success);
  }

  const llmReady = pipeline.llm_ready_count ?? 0;
  const crawlReady = pipeline.crawl_ready_count ?? 0;
  const failed = pipeline.latest_job?.failed_items ?? 0;
  const weighted =
    parsed + Math.max(0, success - parsed) + crawlReady * 0.66 + llmReady * 0.33 + failed;
  return clampPercent((weighted / totalItems) * 100);
}

function stepProgressForStage(
  stageId: PipelineStageId,
  input: {
    processedItems: number;
    totalItems: number;
    responseCount: number;
    parsedCount: number;
    isComplete: boolean;
    pipeline: PipelineStatus | undefined;
  },
): number {
  if (stageId === "verify") return 100;
  if (stageId === "dispatch") {
    return dispatchProgress(input.processedItems, input.totalItems);
  }
  if (stageId === "clean") {
    return cleanStageProgress(input.pipeline, input.totalItems);
  }
  if (input.isComplete) return 100;
  if (input.parsedCount > 0 && input.responseCount > 0) {
    return cleanProgress(input.parsedCount, input.responseCount);
  }
  return 0;
}

export function buildPipelineStepViews(input: {
  stage: PipelineStageId;
  job: PipelineJobView | null;
  pipeline: PipelineStatus | undefined;
  processedItems: number;
  totalItems: number;
  isComplete: boolean;
  isFailed: boolean;
}): PipelineStepView[] {
  const stepIdx = PIPELINE_STAGE_ORDER.indexOf(input.stage);
  const responseCount = input.pipeline?.response_count ?? 0;
  const parsedCount = input.pipeline?.parsed_count ?? 0;
  const setupDone = Boolean(input.pipeline?.latest_job);

  return PIPELINE_STAGE_ORDER.map((id, index) => {
    let status: PipelineStepStatus;
    if (input.isFailed && index === stepIdx) {
      status = "failed";
    } else if (id === "verify" && setupDone) {
      status = "done";
    } else if (index < stepIdx) {
      status = "done";
    } else if (index > stepIdx) {
      status = "queued";
    } else if (id === "dispatch" && input.job?.status === "queued") {
      status = "queued";
    } else {
      status = "processing";
    }

    const progress =
      status === "done"
        ? 100
        : status === "queued"
          ? 0
          : stepProgressForStage(id, {
              processedItems: input.processedItems,
              totalItems: input.totalItems,
              responseCount,
              parsedCount,
              isComplete: input.isComplete,
              pipeline: input.pipeline,
            });

    const copy = PIPELINE_STEP_COPY[id];
    return {
      id,
      index,
      title: copy.title,
      subtitle: copy.subtitle,
      status,
      progress,
    };
  });
}

export function formatPipelineEta(seconds: number | null): string {
  if (seconds == null || seconds <= 0) return "即将完成";
  if (seconds < 60) return "不到 1 分钟";
  const minutes = Math.ceil(seconds / 60);
  if (minutes <= 45) return `约 ${minutes} 分钟`;
  return "约 30–45 分钟";
}

export function pipelinePhaseLabel(stepIndex: number): string {
  return `第 ${stepIndex + 1}/${PIPELINE_STAGE_ORDER.length} 阶段`;
}

export function formatPipelinePhaseHeadline(
  steps: PipelineStepView[],
  currentStepIdx: number,
): string {
  const activeStep = steps[currentStepIdx];
  const label = pipelinePhaseLabel(currentStepIdx);
  return activeStep ? `${label} · ${activeStep.title}` : label;
}
