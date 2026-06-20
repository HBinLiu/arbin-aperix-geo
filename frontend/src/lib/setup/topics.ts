import type { TopicRow } from "@/types";

export const MAX_TOPICS = 5;

export function newTopicRow(partial?: Partial<TopicRow>): TopicRow {
  return {
    id: crypto.randomUUID(),
    name: "",
    selected: true,
    ...partial,
  };
}

export function topicRowsFromNames(names: string[]): TopicRow[] {
  return names.map((name) => newTopicRow({ name, selected: true }));
}

function normalizeTopicNames(names: string[] | undefined): string[] {
  return (names ?? []).map((s) => s.trim()).filter(Boolean);
}

/** 监测主题 → TopicRow（后端应始终返回非空列表） */
export function topicRowsFromMonitoringTopics(monitoringTopics: string[] | undefined): TopicRow[] {
  return topicRowsFromNames(normalizeTopicNames(monitoringTopics));
}

export function selectedTopicRows(rows: TopicRow[]): TopicRow[] {
  return rows.filter((r) => r.selected && r.name.trim());
}

export function selectedTopicNames(rows: TopicRow[]): string[] {
  return selectedTopicRows(rows).map((r) => r.name.trim());
}
