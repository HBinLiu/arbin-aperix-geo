/** Prompt.decision_type 中文标签（与 backend DECISION_TYPE_LABELS 对齐） */

export const DECISION_TYPE_LABELS: Record<string, string> = {
  category_awareness: "品类认知",
  scenario_fit: "场景适配",
  solution_comparison: "选型对比",
  trust_risk: "信任与风险",
  price_value: "价格与性价比",
};

export function decisionTypeLabel(value: string | undefined): string {
  const key = (value ?? "").trim();
  if (!key) return "";
  return DECISION_TYPE_LABELS[key] ?? key;
}
