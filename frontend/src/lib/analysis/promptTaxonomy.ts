export type GeneratedPromptItem = {
  text: string;
  funnel_stage: string;
  search_intent: string;
};

export const FUNNEL_STAGE_LABELS: Record<string, string> = {
  tofu: "TOFU",
  mofu: "MOFU",
  bofu: "BOFU",
};

export const FUNNEL_STAGE_TOOLTIPS: Record<string, string> = {
  tofu: "认知期",
  mofu: "考虑期",
  bofu: "决策期",
};

export const SEARCH_INTENT_LABELS: Record<string, string> = {
  informational: "了解型",
  commercial: "对比型",
  transactional: "交易型",
};

export function funnelStageLabel(stage: string | null | undefined): string {
  const key = (stage ?? "").trim().toLowerCase();
  return FUNNEL_STAGE_LABELS[key] ?? stage ?? "";
}

export function funnelStageTooltip(stage: string | null | undefined): string {
  const key = (stage ?? "").trim().toLowerCase();
  return FUNNEL_STAGE_TOOLTIPS[key] ?? funnelStageLabel(stage);
}

export function searchIntentLabel(intent: string | null | undefined): string {
  const key = (intent ?? "").trim().toLowerCase();
  return SEARCH_INTENT_LABELS[key] ?? intent ?? "";
}

export function searchIntentBadgeLetter(intent: string | null | undefined): string {
  const key = (intent ?? "").trim().toLowerCase();
  if (key === "informational") return "I";
  if (key === "commercial") return "C";
  if (key === "transactional") return "T";
  return key.slice(0, 1).toUpperCase() || "";
}
