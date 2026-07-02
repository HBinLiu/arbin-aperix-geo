import type { AnalysisEntityRef } from "@/types";

/** 分析实体展示名：brand → domain → label（label 为 series key，仅最后兜底） */
export function entityDisplayName(entity: {
  brand?: string | null;
  label: string;
  domain?: string | null;
}): string {
  return (
    entity.brand?.trim() ||
    entity.domain?.trim() ||
    entity.label.trim()
  );
}

/** Chart series keys in entity catalog order (stable across date windows). */
export function entityChartLabels(entities: AnalysisEntityRef[]): string[] {
  return entities.map((entity) => entity.label);
}

/** 图表展示名：series key (多为 domain) → brand 优先，否则 domain */
export function entityLegendLabels(entities: AnalysisEntityRef[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const entity of entities) {
    if (!entity.label) continue;
    out[entity.label] = entityDisplayName(entity);
  }
  return out;
}

export function ownEntityLabel(entities: AnalysisEntityRef[]): string {
  return entities.find((entity) => entity.kind === "own")?.label ?? "";
}

export function focusEntityLabel(
  entities: AnalysisEntityRef[],
  entityId: string | undefined,
): string {
  const focus = entityId ? entities.find((entity) => entity.id === entityId) : undefined;
  return focus?.label ?? ownEntityLabel(entities);
}

export function entityRankFlags(
  entities: AnalysisEntityRef[],
  rowLabel: string,
  focusEntityId: string | undefined,
): { isOwn: boolean; isFocus: boolean } {
  const entity = entities.find((item) => item.label === rowLabel);
  const focusId = focusEntityId ?? entities.find((item) => item.kind === "own")?.id;
  return {
    isOwn: entity?.kind === "own",
    isFocus: entity?.id === focusId,
  };
}
