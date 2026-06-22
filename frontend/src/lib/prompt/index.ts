import type { CSSProperties } from "react";

import type { SubjectPrompt, SubjectTopic } from "@/types";

export const PROMPT_TOPIC_ALL = "all" as const;

export type PromptEnabledFilter = "all" | "enabled" | "disabled";

export type PromptTableRow = {
  id: string;
  index: number;
  text: string;
  topicId: string;
  topicName: string;
  enabled: boolean;
  createdAt: string;
  createdAtLabel: string;
};

export const PROMPT_TABLE_COLUMNS = [
  { id: "select", width: "3%", minWidth: 40 },
  { id: "index", width: "4%", minWidth: 50 },
  { id: "text", width: "40%", minWidth: 220 },
  { id: "topic", width: "20%", minWidth: 160 },
  { id: "createdAt", width: "20%", minWidth: 160 },
  { id: "action", width: "13%", minWidth: 160 },
] as const;

export const PROMPT_TABLE_MIN_WIDTH = PROMPT_TABLE_COLUMNS.reduce(
  (sum, column) => sum + column.minWidth,
  0,
);

/** 工具栏单行布局最小宽度，不足时由外层横向滚动 */
export const PROMPT_TOOLBAR_MIN_WIDTH = 720;

/** Subject 下提示词总配额上限 */
export const PROMPT_QUOTA_LIMIT = 50;

export function subjectPromptRemaining(prompts: SubjectPrompt[]): number {
  return Math.max(0, PROMPT_QUOTA_LIMIT - prompts.length);
}

export function promptColumnStyle(column: { width: string; minWidth: number }): CSSProperties {
  return { width: column.width, minWidth: column.minWidth };
}

export function promptTextCellStyle(minWidth: number): CSSProperties {
  return { minWidth, maxWidth: 0 };
}

export function formatPromptCreatedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const month = date.getMonth() + 1;
  const day = String(date.getDate()).padStart(2, "0");
  const year = date.getFullYear();
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const seconds = String(date.getSeconds()).padStart(2, "0");
  return `${month}/${day}, ${year} ${hours}:${minutes}:${seconds}`;
}

export function topicPromptCounts(
  topics: SubjectTopic[],
  prompts: SubjectPrompt[],
): Map<string, number> {
  const counts = new Map<string, number>();
  for (const topic of topics) counts.set(topic.id, 0);
  for (const prompt of prompts) {
    counts.set(prompt.topic_id, (counts.get(prompt.topic_id) ?? 0) + 1);
  }
  return counts;
}

export function buildPromptTableRows(
  prompts: SubjectPrompt[],
  topics: SubjectTopic[],
  startIndex = 0,
): PromptTableRow[] {
  const topicById = new Map(topics.map((topic) => [topic.id, topic.name]));

  return prompts.map((prompt, offset) => ({
    id: prompt.id,
    index: startIndex + offset + 1,
    text: prompt.text,
    topicId: prompt.topic_id,
    topicName: topicById.get(prompt.topic_id) ?? "—",
    enabled: prompt.enabled,
    createdAt: prompt.created_at,
    createdAtLabel: formatPromptCreatedAt(prompt.created_at),
  }));
}

export function filterPrompts(
  prompts: SubjectPrompt[],
  options: {
    topicId: string;
    enabledFilter: PromptEnabledFilter;
    search: string;
  },
): SubjectPrompt[] {
  const query = options.search.trim().toLowerCase();
  return prompts.filter((prompt) => {
    if (options.topicId !== PROMPT_TOPIC_ALL && prompt.topic_id !== options.topicId) {
      return false;
    }
    if (options.enabledFilter === "enabled" && !prompt.enabled) return false;
    if (options.enabledFilter === "disabled" && prompt.enabled) return false;
    if (query && !prompt.text.toLowerCase().includes(query)) return false;
    return true;
  });
}

export function filterTopicsBySearch(topics: SubjectTopic[], search: string): SubjectTopic[] {
  const query = search.trim().toLowerCase();
  if (!query) return topics;
  return topics.filter((topic) => topic.name.toLowerCase().includes(query));
}

export function parsePromptUploadText(content: string): string[] {
  const lines = content.split(/\r?\n/);
  const values: string[] = [];
  const seen = new Set<string>();
  for (const line of lines) {
    const text = line.trim();
    if (!text || seen.has(text)) continue;
    seen.add(text);
    values.push(text);
  }
  return values;
}
