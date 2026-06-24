import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { clearQueries } from "@/lib/queries";
import {
  isJobTerminal,
} from "@/lib/sampling";
import { derivePipelineState } from "@/lib/sampling/pipeline-state";
import {
  pipelineStreamHub,
  type PipelineStreamMeta,
} from "@/lib/sampling/pipeline-stream";
import type { PipelineStatus } from "@/types";

export type SubjectPipelineState = {
  streamError: string | null;
  job: ReturnType<typeof derivePipelineState>["job"];
  overallProgress: number;
  steps: ReturnType<typeof derivePipelineState>["steps"];
  etaLabel: string;
  canShowMetrics: boolean;
  isRunning: boolean;
  isComplete: boolean;
  isFailed: boolean;
  currentStepIdx: number;
  isLoading: boolean;
};

export const SubjectPipelineContext = createContext<SubjectPipelineState | null>(null);

export function useSubjectPipelineState(subjectId: string): SubjectPipelineState {
  const queryClient = useQueryClient();
  const [pipeline, setPipeline] = useState<PipelineStatus | undefined>();
  const [streamMeta, setStreamMeta] = useState<PipelineStreamMeta>({
    connected: false,
    complete: false,
    error: null,
  });
  const [bootstrapped, setBootstrapped] = useState(false);

  useEffect(() => {
    setBootstrapped(false);
    setPipeline(undefined);
    return pipelineStreamHub.subscribe(subjectId, (status, meta) => {
      setPipeline(status);
      setStreamMeta(meta);
      setBootstrapped(true);
    });
  }, [subjectId]);

  const derived = useMemo(() => derivePipelineState(pipeline), [pipeline]);

  useEffect(() => {
    const status = derived.job?.status;
    if (!status || !isJobTerminal(status) || !derived.isComplete) return;

    clearQueries(queryClient, {
      predicate: (q) =>
        Array.isArray(q.queryKey) &&
        q.queryKey.length >= 2 &&
        q.queryKey[1] === subjectId,
    });
  }, [derived.job?.status, derived.isComplete, subjectId, queryClient]);

  return {
    streamError: streamMeta.error,
    job: derived.job,
    overallProgress: derived.overallProgress,
    steps: derived.steps,
    etaLabel: derived.etaLabel,
    canShowMetrics: derived.canShowMetrics,
    isRunning: derived.isRunning,
    isComplete: derived.isComplete,
    isFailed: derived.isFailed,
    currentStepIdx: derived.currentStepIdx,
    isLoading: !bootstrapped && !pipeline,
  };
}

export function useSubjectPipeline(): SubjectPipelineState {
  const value = useContext(SubjectPipelineContext);
  if (!value) {
    throw new Error("useSubjectPipeline must be used within SubjectPipelineProvider");
  }
  return value;
}

