import type { KnowledgeSource, SubjectKnowledge } from "@/types";

export type KnowledgeSourceFilter = "all" | "upload" | "homepage" | "user_input";

export const KNOWLEDGE_SOURCE_FILTERS: { id: KnowledgeSourceFilter; label: string }[] = [
  { id: "all", label: "全部" },
  { id: "upload", label: "文档" },
  { id: "homepage", label: "链接" },
  { id: "user_input", label: "录入" },
];

export type KnowledgeSourceRowStatus = {
  label: string;
  variant: "success" | "warning" | "error" | "info" | "gray";
};

export function knowledgeSourceRowStatus(
  source: KnowledgeSource,
  knowledge: SubjectKnowledge | null,
): KnowledgeSourceRowStatus {
  if (source.parse_status !== "ok") {
    return { label: source.parse_error ? "解析失败" : source.parse_status, variant: "error" };
  }
  if (knowledge?.index_status === "indexing" || knowledge?.index_status === "pending") {
    return { label: "索引中", variant: "info" };
  }
  if (knowledge?.status === "stale") {
    return { label: "待更新", variant: "warning" };
  }
  if (knowledge?.index_status === "failed") {
    return { label: "索引失败", variant: "error" };
  }
  if (
    knowledge &&
    knowledge.index_status === "indexed" &&
    knowledge.indexed_version === knowledge.version
  ) {
    return { label: "已处理", variant: "success" };
  }
  return { label: "已收录", variant: "gray" };
}

export function filterKnowledgeSources(
  sources: KnowledgeSource[],
  filter: KnowledgeSourceFilter,
  query: string,
): KnowledgeSource[] {
  const normalized = query.trim().toLowerCase();
  return sources.filter((source) => {
    if (filter !== "all" && source.kind !== filter) return false;
    if (!normalized) return true;
    const haystack = [
      source.title,
      source.uri,
      source.raw_text_preview,
      source.raw_text ?? "",
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(normalized);
  });
}
