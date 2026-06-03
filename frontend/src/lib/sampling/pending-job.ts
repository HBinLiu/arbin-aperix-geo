const PENDING_JOB_KEY = "aperix_pending_job";

export function setPendingJobId(subjectId: string, jobId: string): void {
  sessionStorage.setItem(`${PENDING_JOB_KEY}:${subjectId}`, jobId);
}

export function getPendingJobId(subjectId: string): string | null {
  return sessionStorage.getItem(`${PENDING_JOB_KEY}:${subjectId}`);
}

export function clearPendingJobId(subjectId: string): void {
  sessionStorage.removeItem(`${PENDING_JOB_KEY}:${subjectId}`);
}
