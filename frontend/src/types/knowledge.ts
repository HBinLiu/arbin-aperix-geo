export type KnowledgeStatus = "draft" | "verified" | "stale";

export type KnowledgeIndexStatus = "pending" | "indexing" | "indexed" | "failed" | "skipped";

export type KnowledgeExtractStatus = "pending" | "ready" | "failed" | "skipped";

export type KnowledgeSourceKind = "user_input" | "upload" | "homepage" | string;

export type KnowledgeNodeType =
  | "brand"
  | "product"
  | "audience"
  | "pain"
  | "differentiator"
  | "competitor"
  | "scenario"
  | "proof"
  | string;

export type KnowledgeEdgeType =
  | "offers"
  | "serves"
  | "solves"
  | "differentiates_by"
  | "competes_with"
  | "used_in"
  | "part_of"
  | "supported_by"
  | string;

export type SubjectKnowledge = {
  id: string;
  subject_id: string;
  status: KnowledgeStatus | string;
  version: number;
  index_status: KnowledgeIndexStatus | string;
  indexed_version: number;
  index_error: string;
  extract_status?: KnowledgeExtractStatus | string;
  extract_error?: string;
  node_count?: number;
  edge_count?: number;
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

export type KnowledgeGraphNode = {
  id: string;
  type: KnowledgeNodeType;
  label: string;
  aliases: string[];
  source_ids: string[];
  confidence: number;
};

export type KnowledgeGraphEdge = {
  id: string;
  type: KnowledgeEdgeType;
  from: string;
  to: string;
  label: string;
  source_ids: string[];
  evidence: string;
  confidence: number;
};

export type KnowledgeGraph = {
  schema_version: number;
  extract_status: KnowledgeExtractStatus | string;
  extract_error: string;
  extracted_at: string;
  nodes: KnowledgeGraphNode[];
  edges: KnowledgeGraphEdge[];
};

export type SubjectKnowledgeDetail = {
  knowledge: SubjectKnowledge | null;
  sources: KnowledgeSource[];
  chunk_count: number;
  graph?: KnowledgeGraph | null;
};
