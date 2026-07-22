import type {
  KnowledgeExtractStatus,
  KnowledgeIndexStatus,
  KnowledgeNodeType,
  KnowledgeSource,
  KnowledgeSourceKind,
} from "@/types";

const INDEX_STATUS_LABELS: Record<string, string> = {
  pending: "待索引",
  indexing: "索引中",
  indexed: "已索引",
  failed: "索引失败",
  skipped: "已跳过",
};

const EXTRACT_STATUS_LABELS: Record<string, string> = {
  pending: "图谱抽取中",
  ready: "图谱已就绪",
  failed: "图谱抽取失败",
  skipped: "图谱已跳过",
};

const SOURCE_KIND_LABELS: Record<string, string> = {
  user_input: "录入",
  upload: "文档",
  homepage: "链接",
};

const NODE_TYPE_LABELS: Record<string, string> = {
  brand: "品牌",
  product: "产品",
  audience: "人群",
  pain: "痛点",
  differentiator: "差异化",
  competitor: "竞品",
  scenario: "场景",
  proof: "证据",
};

export function knowledgeIndexStatusLabel(status: KnowledgeIndexStatus | string): string {
  return INDEX_STATUS_LABELS[status] ?? status;
}

export function knowledgeExtractStatusLabel(status: KnowledgeExtractStatus | string): string {
  return EXTRACT_STATUS_LABELS[status] ?? status;
}

export function knowledgeNodeTypeLabel(type: KnowledgeNodeType | string): string {
  return NODE_TYPE_LABELS[type] ?? type;
}

export function knowledgeSourceKindLabel(kind: KnowledgeSourceKind): string {
  return SOURCE_KIND_LABELS[kind] ?? kind;
}

export function formatKnowledgeDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatFileSize(size: number): string {
  if (size <= 0) return "—";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export function knowledgeNeedsReindex(input: {
  version: number;
  indexed_version: number;
  index_status: string;
}): boolean {
  return input.index_status !== "indexing" && input.indexed_version !== input.version;
}

/** Badge label: prefer version drift over raw index_status when they disagree. */
export function knowledgeIndexDisplayLabel(input: {
  version: number;
  indexed_version: number;
  index_status: string;
}): string {
  if (input.index_status === "indexing") {
    return knowledgeIndexStatusLabel("indexing");
  }
  if (input.index_status === "failed") {
    return knowledgeIndexStatusLabel("failed");
  }
  if (knowledgeNeedsReindex(input)) {
    return "待重新索引";
  }
  if (input.index_status === "pending") {
    return knowledgeIndexStatusLabel("pending");
  }
  return knowledgeIndexStatusLabel(input.index_status);
}

export function knowledgeSourceRows(sources: KnowledgeSource[]): KnowledgeSource[] {
  return [...sources].sort((a, b) => a.sort_order - b.sort_order || a.title.localeCompare(b.title));
}
