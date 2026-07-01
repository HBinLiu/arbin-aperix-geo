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

export type SetupMonitoringTopic = {
  name: string;
};

/** 监测主题 API → TopicRow */
export function topicRowsFromSetupTopics(topics: SetupMonitoringTopic[] | undefined): TopicRow[] {
  return (topics ?? [])
    .map((item) => item.name?.trim() ?? "")
    .filter(Boolean)
    .map((name) => newTopicRow({ name, selected: true }));
}

export function selectedTopicRows(rows: TopicRow[]): TopicRow[] {
  return rows.filter((r) => r.selected && r.name.trim());
}

export function selectedTopicNames(rows: TopicRow[]): string[] {
  return selectedTopicRows(rows).map((r) => r.name.trim());
}
