import { api } from "@/api/client";
import type { SamplingJob } from "@/types";

export async function retrySamplingJob(subjectId: string): Promise<SamplingJob> {
  const { data } = await api.post<SamplingJob>(`/subjects/${subjectId}/sampling-jobs/retry`);
  return data;
}
