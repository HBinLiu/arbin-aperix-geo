import type { TopicRow } from "@/types";

/** setup「审查主题」默认兜底（无微观利基 keywords 时使用） */
const FALLBACK_TOPIC_NAMES = ["品牌认知与提及", "产品与竞品对比", "用户评价与舆情"];

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

export function topicNamesFromDiscover(microKeywords: string[] | undefined): string[] {
  const keywords = (microKeywords ?? []).map((s) => s.trim()).filter(Boolean);
  if (keywords.length > 0) {
    return keywords;
  }
  return [...FALLBACK_TOPIC_NAMES];
}

export function topicRowsFromDiscover(microKeywords: string[] | undefined): TopicRow[] {
  return topicRowsFromNames(topicNamesFromDiscover(microKeywords));
}

export function selectedTopicRows(rows: TopicRow[]): TopicRow[] {
  return rows.filter((r) => r.selected && r.name.trim());
}

export function selectedTopicNames(rows: TopicRow[]): string[] {
  return selectedTopicRows(rows).map((r) => r.name.trim());
}
