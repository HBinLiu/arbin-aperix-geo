import type { TopicRow } from "@/types";

/** 监测主题兜底（仅 monitoring_topics 为空时使用） */
const FALLBACK_MONITORING_TOPIC_NAMES = ["品牌认知与提及", "产品与竞品对比", "用户评价与舆情"];

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

/** 监测主题 → TopicRow（空时使用监测主题兜底） */
export function topicRowsFromMonitoringTopics(monitoringTopics: string[] | undefined): TopicRow[] {
  const topics = normalizeTopicNames(monitoringTopics);
  if (topics.length > 0) {
    return topicRowsFromNames(topics);
  }
  return topicRowsFromNames(FALLBACK_MONITORING_TOPIC_NAMES);
}

export function selectedTopicRows(rows: TopicRow[]): TopicRow[] {
  return rows.filter((r) => r.selected && r.name.trim());
}

export function selectedTopicNames(rows: TopicRow[]): string[] {
  return selectedTopicRows(rows).map((r) => r.name.trim());
}
