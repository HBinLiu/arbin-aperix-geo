import type {
  KnowledgeIndexStatus,
  KnowledgeSource,
  KnowledgeSourceKind,
  KnowledgeStatus,
} from "@/types";

const STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  verified: "已验证",
  stale: "待更新",
};

const INDEX_STATUS_LABELS: Record<string, string> = {
  pending: "待索引",
  indexing: "索引中",
  indexed: "已索引",
  failed: "索引失败",
  skipped: "已跳过",
};

const SOURCE_KIND_LABELS: Record<string, string> = {
  user_input: "录入",
  upload: "文档",
  homepage: "链接",
};

export function knowledgeStatusLabel(status: KnowledgeStatus | string): string {
  return STATUS_LABELS[status] ?? status;
}

export function knowledgeIndexStatusLabel(status: KnowledgeIndexStatus | string): string {
  return INDEX_STATUS_LABELS[status] ?? status;
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

export function knowledgeSourceRows(sources: KnowledgeSource[]): KnowledgeSource[] {
  return [...sources].sort((a, b) => a.sort_order - b.sort_order || a.title.localeCompare(b.title));
}
