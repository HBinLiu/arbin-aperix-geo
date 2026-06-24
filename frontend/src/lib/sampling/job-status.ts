import type { PipelineStatus } from "@/types";

export function isJobTerminal(status: string): boolean {
  return status === "succeed" || status === "partial" || status === "failed";
}

export function isPipelineComplete(status: PipelineStatus | undefined): boolean {
  if (!status) return false;
  const job = status.latest_job;
  if (!job?.status || !isJobTerminal(job.status)) return false;
  return status.response_count > 0 && status.parsed_count >= status.response_count;
}
