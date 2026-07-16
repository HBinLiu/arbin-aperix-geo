import { ACADEMY_BLOCK_SLUGS } from "@shared/academy/blocks";
import type { AcademyTocItem } from "@shared/academy";

type LexicalNode = {
  type?: string;
  tag?: string;
  fields?: {
    blockType?: string;
    anchorId?: string | null;
    title?: string | null;
  };
  children?: LexicalNode[];
  text?: string;
};

export function slugifyHeading(text: string): string {
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

function walkNodesInOrder(
  nodes: LexicalNode[] | undefined,
  visit: (node: LexicalNode) => void,
) {
  for (const node of nodes ?? []) {
    visit(node);
    walkNodesInOrder(node.children, visit);
  }
}

/** 从 Lexical JSON 提取目录：H2 +「60 秒简报」+ 带标题的「双栏信息卡」（按文档顺序） */
export function extractAcademyToc(content: unknown): AcademyTocItem[] {
  if (!content || typeof content !== "object" || !("root" in content)) return [];

  const root = (content as { root?: { children?: LexicalNode[] } }).root;
  const items: AcademyTocItem[] = [];
  const usedIds = new Set<string>();

  const pushItem = (rawId: string, label: string) => {
    const trimmedLabel = label.trim();
    if (!trimmedLabel) return;

    let id = rawId.trim() || slugifyHeading(trimmedLabel);
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
      label: trimmedLabel,
    });
  };

  walkNodesInOrder(root?.children, (node) => {
    if (node.type === "heading" && node.tag === "h2") {
      pushItem(slugifyHeading(nodePlainText(node)), nodePlainText(node));
      return;
    }

    if (node.type !== "block") return;
    const blockType = node.fields?.blockType;
    if (blockType !== ACADEMY_BLOCK_SLUGS.brief && blockType !== ACADEMY_BLOCK_SLUGS.infoGrid) return;

    const title = node.fields?.title?.trim();
    if (!title) return;

    const anchorId =
      node.fields?.anchorId?.trim() ||
      (blockType === ACADEMY_BLOCK_SLUGS.brief ? "brief" : slugifyHeading(title));
    pushItem(anchorId, title);
  });

  return items;
}
