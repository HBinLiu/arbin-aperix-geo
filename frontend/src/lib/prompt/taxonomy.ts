import type { PromptTaxonomy, PromptTaxonomyOption } from "@/types";

export function taxonomyOptionLabel(
  options: PromptTaxonomyOption[],
  value: string | null | undefined,
): string {
  const key = (value ?? "").trim();
  if (!key) return "—";
  return options.find((option) => option.value === key)?.label ?? key;
}

export function taxonomySelectOptions(options: PromptTaxonomyOption[]) {
  return options.map((option) => ({ value: option.value, label: option.label }));
}

/** 按 value 或中文 label 解析 taxonomy 选项（CSV 导入等）。 */
export function resolveTaxonomyOptionValue(
  options: PromptTaxonomyOption[],
  raw: string,
): string | null {
  const key = raw.trim();
  if (!key) return null;
  const lower = key.toLowerCase();
  const byValue = options.find((option) => option.value.toLowerCase() === lower);
  if (byValue) return byValue.value;
  const byLabel = options.find(
    (option) => option.label === key || option.label.toLowerCase() === lower,
  );
  return byLabel?.value ?? null;
}

export function taxonomyOptionLabels(options: PromptTaxonomyOption[]): string {
  return options.map((option) => option.label).join("、");
}

export function fallbackPromptTaxonomy(): PromptTaxonomy {
  return {
    funnel_stages: [],
    search_intents: [],
    decision_types: [],
    default_funnel_stage: "mofu",
    default_search_intent: "commercial",
    default_decision_type: "category_awareness",
  };
}
