import type { KnowledgeGraph, KnowledgeGraphEdge, KnowledgeGraphNode } from "@/types";

export type GraphViewNode = {
  id: string;
  label: string;
  type: string;
  aliases: string[];
};

export type GraphViewLink = {
  id: string;
  /** Consumed by force-graph (may be mutated into node objects). */
  source: string;
  target: string;
  /** Stable ends for UI / neighbor lookup. */
  fromId: string;
  toId: string;
  type: string;
  label: string;
};

export type GraphViewData = {
  nodes: GraphViewNode[];
  links: GraphViewLink[];
};

export function toGraphViewData(graph: KnowledgeGraph | null | undefined): GraphViewData {
  const nodes = (graph?.nodes ?? []).map(toViewNode);
  const nodeIds = new Set(nodes.map((node) => node.id));
  const links = (graph?.edges ?? [])
    .map(toViewLink)
    .filter((link) => nodeIds.has(link.fromId) && nodeIds.has(link.toId));
  return { nodes, links };
}

/** Type filter only; brand is always kept. Search is highlight-only (see matchNodeIds). */
export function filterGraphViewData(
  data: GraphViewData,
  options: { enabledTypes: ReadonlySet<string> },
): GraphViewData {
  const { enabledTypes } = options;
  const nodes = data.nodes.filter((node) => node.type === "brand" || enabledTypes.has(node.type));
  const nodeIds = new Set(nodes.map((node) => node.id));
  const links = data.links.filter((link) => nodeIds.has(link.fromId) && nodeIds.has(link.toId));
  return { nodes, links };
}

export function matchNodeIds(nodes: GraphViewNode[], query: string): Set<string> | null {
  const q = query.trim().toLowerCase();
  if (!q) return null;
  return new Set(
    nodes
      .filter(
        (node) =>
          node.label.toLowerCase().includes(q) ||
          node.aliases.some((alias) => alias.toLowerCase().includes(q)),
      )
      .map((node) => node.id),
  );
}

export function neighborIdsForNode(data: GraphViewData, nodeId: string | null): Set<string> {
  const ids = new Set<string>();
  if (!nodeId) return ids;
  ids.add(nodeId);
  for (const link of data.links) {
    if (link.fromId === nodeId || link.toId === nodeId) {
      ids.add(link.fromId);
      ids.add(link.toId);
    }
  }
  return ids;
}

export function countNodesByType(nodes: GraphViewNode[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const node of nodes) {
    counts[node.type] = (counts[node.type] ?? 0) + 1;
  }
  return counts;
}

function toViewNode(node: KnowledgeGraphNode): GraphViewNode {
  return {
    id: node.id,
    label: node.label,
    type: node.type,
    aliases: node.aliases ?? [],
  };
}

function toViewLink(edge: KnowledgeGraphEdge): GraphViewLink {
  return {
    id: edge.id,
    source: edge.from,
    target: edge.to,
    fromId: edge.from,
    toId: edge.to,
    type: edge.type,
    label: edge.label || edge.type,
  };
}
