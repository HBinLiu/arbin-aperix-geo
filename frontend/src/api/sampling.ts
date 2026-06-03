import { api } from "@/api/client";
import type { PipelineStatus, SamplingJob } from "@/types";

export async function fetchSamplingJob(jobId: string): Promise<SamplingJob> {
  const { data } = await api.get<SamplingJob>(`/sampling-jobs/${jobId}`);
  return data;
}

export async function fetchPipelineStatus(subjectId: string): Promise<PipelineStatus> {
  const { data } = await api.get<PipelineStatus>(`/subjects/${subjectId}/pipeline-status`);
  return data;
}
