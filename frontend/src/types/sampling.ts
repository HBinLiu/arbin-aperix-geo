export type SamplingJob = {
  id: string;
  tenant_id: string;
  subject_id: string;
  status: "queued" | "running" | "succeed" | "partial" | "failed";
  total_items: number;
  completed_items: number;
  failed_items: number;
  error_message: string;
  created_at: string;
  started_at: string;
  finished_at: string;
};

export type PipelineJobStatus = SamplingJob["status"];

/** SSE / 进度 UI 使用的 job 视图（来自 latest_job，不含 tenant / subject）。 */
export type PipelineJobView = {
  id: string;
  status: PipelineJobStatus;
  total_items: number;
  failed_items: number;
  error_message: string;
  started_at: string | null;
};

export type PipelineStatus = {
  stage: "verify" | "dispatch" | "clean" | "analyze";
  /** Celery worker 子阶段（llm / crawl / parse），与 UI 四步 stage 不同。 */
  worker_phase: "llm" | "crawl" | "parse" | null;
  latest_job: {
    id: string;
    status: string;
    total_items: number;
    completed_items: number;
    failed_items: number;
    error_message: string;
    created_at: string;
    started_at: string | null;
    finished_at: string | null;
  } | null;
  llm_pending_count: number;
  llm_ready_count: number;
  crawl_ready_count: number;
  response_count: number;
  parsed_count: number;
};
