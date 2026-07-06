export type KnowledgeStatus = "draft" | "verified" | "stale";

export type KnowledgeIndexStatus = "pending" | "indexing" | "indexed" | "failed" | "skipped";

export type KnowledgeSourceKind = "user_input" | "upload" | "homepage" | string;

export type SubjectKnowledge = {
  id: string;
  subject_id: string;
  status: KnowledgeStatus | string;
  version: number;
  index_status: KnowledgeIndexStatus | string;
  indexed_version: number;
  index_error: string;
  verified_at: string;
  updated_at: string;
};

export type KnowledgeSource = {
  id: string;
  kind: KnowledgeSourceKind;
  title: string;
  uri: string;
  mime_type: string;
  file_size: number;
  char_count: number;
  parse_status: string;
  parse_error: string;
  sort_order: number;
  raw_text_preview: string;
  raw_text?: string;
  created_at: string;
  updated_at: string;
};

export type SubjectKnowledgeDetail = {
  knowledge: SubjectKnowledge | null;
  sources: KnowledgeSource[];
  chunk_count: number;
};
