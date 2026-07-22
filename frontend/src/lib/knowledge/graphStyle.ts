/** Visual tokens for knowledge graph node types (drawn on project dark canvas). */

export const KNOWLEDGE_GRAPH_NODE_TYPES = [
  "brand",
  "product",
  "audience",
  "pain",
  "differentiator",
  "competitor",
  "scenario",
  "proof",
] as const;

export type KnowledgeGraphViewNodeType = (typeof KNOWLEDGE_GRAPH_NODE_TYPES)[number];

export const KNOWLEDGE_GRAPH_BRAND_COLOR = "#FFB300";

type NodeStyle = {
  color: string;
  /** World-coordinate radius (D3 SVG; scales with zoom). */
  radius: number;
};

const NODE_STYLES: Record<string, NodeStyle> = {
  brand: { color: KNOWLEDGE_GRAPH_BRAND_COLOR, radius: 30 },
  product: { color: "#38BDF8", radius: 16 },
  audience: { color: "#C084FC", radius: 15 },
  pain: { color: "#FB7185", radius: 15 },
  differentiator: { color: "#2DD4BF", radius: 15 },
  competitor: { color: "#F97316", radius: 15 },
  scenario: { color: "#818CF8", radius: 15 },
  proof: { color: "#A3E635", radius: 13 },
};

const FALLBACK: NodeStyle = { color: "#A3E635", radius: 14 };

export function knowledgeGraphNodeStyle(type: string): NodeStyle {
  return NODE_STYLES[type] ?? FALLBACK;
}
