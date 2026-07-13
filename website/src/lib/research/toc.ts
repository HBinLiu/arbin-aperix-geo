import type { ResearchTocItem } from "@shared/research";

type LexicalNode = {
  type?: string;
  tag?: string;
  children?: LexicalNode[];
  text?: string;
};

function slugifyHeading(text: string): string {
  return text
    .trim()
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s-]/gu, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

function nodePlainText(node: LexicalNode): string {
  if (node.type === "text" && node.text) return node.text;
  return (node.children ?? []).map(nodePlainText).join("");
}

function walkNodes(nodes: LexicalNode[] | undefined, visit: (node: LexicalNode) => void) {
  for (const node of nodes ?? []) {
    visit(node);
    walkNodes(node.children, visit);
  }
}

/** 目录展示用：取 H2 在常用分隔符前的部分（正文仍显示完整标题） */
export function formatTocLabel(fullLabel: string): string {
  const trimmed = fullLabel.trim();
  if (!trimmed) return trimmed;

  const separator = /\s*(?:[：:|｜/／·•>→]|\s+[-–—]+\s+|[—–])\s*/u;
  const [head] = trimmed.split(separator);
  return (head ?? trimmed).trim() || trimmed;
}

/** 从 Lexical JSON 提取 H2 目录（与正文 heading converter 的 id 规则一致） */
export function extractResearchToc(content: unknown): ResearchTocItem[] {
  if (!content || typeof content !== "object" || !("root" in content)) return [];

  const root = (content as { root?: { children?: LexicalNode[] } }).root;
  const items: ResearchTocItem[] = [];
  const usedIds = new Set<string>();

  walkNodes(root?.children, (node) => {
    if (node.type !== "heading" || node.tag !== "h2") return;

    const fullLabel = nodePlainText(node).trim();
    if (!fullLabel) return;

    let id = slugifyHeading(fullLabel);
    if (!id) id = `section-${items.length + 1}`;
    let uniqueId = id;
    let suffix = 2;
    while (usedIds.has(uniqueId)) {
      uniqueId = `${id}-${suffix}`;
      suffix += 1;
    }
    usedIds.add(uniqueId);

    items.push({
      id: uniqueId,
      number: String(items.length + 1).padStart(2, "0"),
      label: formatTocLabel(fullLabel),
    });
  });

  return items;
}

export { slugifyHeading };
