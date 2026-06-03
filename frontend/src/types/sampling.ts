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

export type PipelineStatus = {
  stage: "verify" | "dispatch" | "clean" | "analyze";
  latest_job: {
    id: string;
    status: string;
    total_items: number;
    completed_items: number;
    failed_items: number;
    error_message: string;
    created_at: string;
    started_at: string;
    finished_at: string;
  } | null;
  response_count: number;
  parsed_count: number;
};
