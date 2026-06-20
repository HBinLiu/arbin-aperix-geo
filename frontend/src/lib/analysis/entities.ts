import type { AnalysisEntityRef } from "@/types";

/** Chart series keys in entity catalog order (stable across date windows). */
export function entityChartLabels(entities: AnalysisEntityRef[]): string[] {
  return entities.map((entity) => entity.label);
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
