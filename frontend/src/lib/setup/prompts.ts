import type { PromptRow, TopicRow } from "@/types";

const PROMPTS_PER_TOPIC = 10;

export function newPromptRow(partial?: Partial<PromptRow>): PromptRow {
  return {
    id: crypto.randomUUID(),
    text: "",
    topicId: "",
    selected: true,
    ...partial,
  };
}

export function maxPromptCount(topicCount: number): number {
  return Math.max(0, topicCount * PROMPTS_PER_TOPIC);
}

function normalizeTopicName(name: string): string {
  return name.trim().toLowerCase();
}

function findTopicItem(
  topic: TopicRow,
  items: { topic: string; prompts: string[] }[],
): { topic: string; prompts: string[] } | undefined {
  const key = normalizeTopicName(topic.name);
  return (
    items.find((i) => normalizeTopicName(i.topic) === key) ??
    items.find((i) => normalizeTopicName(i.topic).includes(key) || key.includes(normalizeTopicName(i.topic)))
  );
}

export function promptRowsFromGenerated(
  topics: TopicRow[],
  items: { topic: string; prompts: string[] }[],
): PromptRow[] {
  const rows: PromptRow[] = [];
  for (const topic of topics) {
    const item = findTopicItem(topic, items);
    const texts = (item?.prompts ?? []).map((s) => s.trim()).filter(Boolean).slice(0, PROMPTS_PER_TOPIC);
    for (const text of texts) {
      rows.push(newPromptRow({ text, topicId: topic.id, selected: true }));
    }
  }
  return rows;
}

export function selectedPromptRows(rows: PromptRow[]): PromptRow[] {
  return rows.filter((r) => r.selected && r.text.trim());
}
