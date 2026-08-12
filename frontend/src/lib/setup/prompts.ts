import type { GeneratedPromptItem, PromptRow, TopicRow } from "@/types";

const PROMPT_PER_TOPIC = 5;

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
  return Math.max(0, topicCount * PROMPT_PER_TOPIC);
}

function normalizeTopicName(name: string): string {
  return name.trim().toLowerCase();
}

function findTopicItem(
  topic: TopicRow,
  items: { topic: string; prompts: GeneratedPromptItem[] }[],
): { topic: string; prompts: GeneratedPromptItem[] } | undefined {
  const key = normalizeTopicName(topic.name);
  return items.find((i) => normalizeTopicName(i.topic) === key);
}

export function promptRowsFromGenerated(
  topics: TopicRow[],
  items: { topic: string; prompts: GeneratedPromptItem[] }[],
): PromptRow[] {
  const rows: PromptRow[] = [];
  for (const topic of topics) {
    const item = findTopicItem(topic, items);
    const prompts = (item?.prompts ?? []).slice(0, PROMPT_PER_TOPIC);
    for (const prompt of prompts) {
      const text = prompt.text.trim();
      if (!text) continue;
      rows.push(
        newPromptRow({
          text,
          topicId: topic.id,
          selected: true,
          funnelStage: prompt.funnel_stage,
          searchIntent: prompt.search_intent,
          decisionType: prompt.decision_type,
        }),
      );
    }
  }
  return rows;
}

export function selectedPromptRows(rows: PromptRow[]): PromptRow[] {
  return rows.filter((r) => r.selected && r.text.trim());
}
