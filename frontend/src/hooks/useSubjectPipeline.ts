import { useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchPipelineStatus, fetchSamplingJob } from "@/api/sampling";
import { queryKeys } from "@/lib/queries";
import {
  clearPendingJobId,
  getPendingJobId,
  isJobTerminal,
} from "@/lib/sampling";
import type { PipelineStatus, SamplingJob } from "@/types";

const STAGE_ORDER = ["verify", "dispatch", "clean", "analyze"] as const;

export type PipelineStage = PipelineStatus["stage"];

function jobFromPipeline(pipeline: PipelineStatus | undefined): SamplingJob | null {
  if (!pipeline?.latest_job) return null;
  const j = pipeline.latest_job;
  return {
    id: j.id,
    tenant_id: "",
    subject_id: "",
    status: j.status as SamplingJob["status"],
    total_items: j.total_items,
    completed_items: j.completed_items,
    failed_items: j.failed_items,
    error_message: j.error_message,
    created_at: j.created_at,
    started_at: j.started_at,
    finished_at: j.finished_at,
  };
}

export function useSubjectPipeline(subjectId: string) {
  const queryClient = useQueryClient();
  const pendingJobId = getPendingJobId(subjectId);

  const pipelineQuery = useQuery({
    queryKey: queryKeys.pipelineStatus(subjectId),
    queryFn: () => fetchPipelineStatus(subjectId),
    refetchInterval: (q) => {
      const stage = q.state.data?.stage;
      return stage === "dispatch" || stage === "clean" ? 4000 : false;
    },
  });

  const jobId = pendingJobId ?? pipelineQuery.data?.latest_job?.id ?? null;

  const jobQuery = useQuery({
    queryKey: queryKeys.samplingJob(jobId ?? "none"),
    queryFn: () => fetchSamplingJob(jobId!),
    enabled: Boolean(jobId),
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      return status && !isJobTerminal(status) ? 4000 : false;
    },
  });

  const pipeline = pipelineQuery.data;
  const job = jobQuery.data ?? jobFromPipeline(pipeline);
  const stage = pipeline?.stage ?? "verify";

  const totalItems = job?.total_items ?? 0;
  const processedItems = Math.min(
    totalItems,
    (pipeline?.response_count ?? 0) +
      (job?.failed_items ?? pipeline?.latest_job?.failed_items ?? 0),
  );
  const jobProgress =
    totalItems > 0 ? Math.round((processedItems / totalItems) * 100) : undefined;

  const canShowMetrics =
    stage === "analyze" ||
    (pipeline?.parsed_count ?? 0) > 0 ||
    Boolean(job?.status && isJobTerminal(job.status) && (job.completed_items ?? 0) > 0);

  const isComplete =
    Boolean(job?.status && isJobTerminal(job.status)) &&
    (pipeline?.response_count ?? 0) > 0 &&
    (pipeline?.parsed_count ?? 0) >= (pipeline?.response_count ?? 0);

  const isRunning = !isComplete && (stage === "dispatch" || stage === "clean");
  const isFailed =
    job?.status === "failed" &&
    (pipeline?.parsed_count ?? 0) === 0 &&
    (pipeline?.response_count ?? 0) === 0;

  const currentStepIdx = STAGE_ORDER.indexOf(stage);

  useEffect(() => {
    const status = jobQuery.data?.status;
    if (!status || !isJobTerminal(status)) return;

    clearPendingJobId(subjectId);
    void queryClient.invalidateQueries({ queryKey: queryKeys.pipelineStatus(subjectId) });
    void queryClient.invalidateQueries({
      predicate: (q) =>
        Array.isArray(q.queryKey) &&
        q.queryKey.length >= 2 &&
        q.queryKey[1] === subjectId,
    });
  }, [jobQuery.data?.status, subjectId, queryClient]);

  return {
    pipelineQuery,
    jobQuery,
    stage,
    job,
    jobProgress,
    processedItems,
    totalItems,
    canShowMetrics,
    isRunning,
    isComplete,
    isFailed,
    currentStepIdx,
    isLoading: pipelineQuery.isLoading,
  };
}
