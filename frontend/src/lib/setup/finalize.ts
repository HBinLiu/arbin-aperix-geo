import { rowsToPersist, selectedPromptRows, selectedTopicRows } from "@/lib/setup";
import type { FinalizeSetupInput } from "@/types";

export function buildFinalizePayload(input: FinalizeSetupInput) {
  const { competitors } = rowsToPersist(input.mode, input.competitorRows);
  const topicsToPersist = selectedTopicRows(input.topicRows);
  const domain = input.mode === "domain" ? input.domain.trim() : "";
  const brand = input.mode === "brand" ? input.brand.trim() : "";
  const sessionId = input.sessionId.trim();

  const promptsByTopicId = new Map<
    string,
    { text: string; funnel_stage: string; search_intent: string }[]
  >();
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
    type: input.mode,
    ...(domain ? { domain } : {}),
    ...(brand ? { brand } : {}),
    monitoring_scope: {
      region: input.region,
      language: input.language,
    },
    ...(sessionId ? { setup_session_id: sessionId } : {}),
    competitors,
    topics: topicsToPersist.map((t) => ({
      name: t.name.trim(),
      prompts: promptsByTopicId.get(t.id) ?? [],
    })),
  };
}
