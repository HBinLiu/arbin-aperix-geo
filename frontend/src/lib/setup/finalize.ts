import { selectedPromptRows, selectedTopicRows } from "@/lib/setup";
import type { FinalizeSetupInput } from "@/types";

export function buildFinalizePayload(input: FinalizeSetupInput) {
  const topicsToPersist = selectedTopicRows(input.topicRows);

  const promptsByTopicId = new Map<string, { text: string; funnel_stage: string; search_intent: string }[]>();
  for (const row of selectedPromptRows(input.promptRows)) {
    const list = promptsByTopicId.get(row.topicId) ?? [];
    list.push({
      text: row.text.trim(),
      funnel_stage: row.funnelStage ?? "mofu",
      search_intent: row.searchIntent ?? "commercial",
    });
    promptsByTopicId.set(row.topicId, list);
  }

  return {
    topics: topicsToPersist.map((t) => ({
      name: t.name.trim(),
      prompts: promptsByTopicId.get(t.id) ?? [],
    })),
  };
}
