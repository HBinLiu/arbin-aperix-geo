import { RESEARCH_BLOCK_SLUGS } from "@shared/research/blocks";
import type { HTMLConvertersFunction } from "@payloadcms/richtext-lexical/html";
import { convertLexicalToHTML } from "@payloadcms/richtext-lexical/html";
import { defaultColors } from "@payloadcms/richtext-lexical/defaultColors";
import type { SerializedEditorState, SerializedTextNode } from "lexical";

import { resolveResearchMediaAlt, resolveResearchMediaUrl } from "@/lib/research/media";
import { slugifyHeading } from "@/lib/research/toc";
import { resolveSiteCopy } from "@/lib/site";

const textStateConfig = {
  color: {
    ...defaultColors.text,
    ...defaultColors.background,
  },
} as const;

const NODE_STATE_KEY = "$";

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function cssToInlineStyle(css: Record<string, string>): string {
  return Object.entries(css)
    .map(([property, value]) => `${property}:${value}`)
    .join(";");
}

const researchHtmlConverters: HTMLConvertersFunction = ({ defaultConverters }) => ({
  ...defaultConverters,
  text: (args) => {
    const base =
      typeof defaultConverters.text === "function" ? defaultConverters.text(args) : args.node.text;

    const nodeState = (args.node as SerializedTextNode & { $?: Record<string, string> })[NODE_STATE_KEY];
    if (!nodeState) return base;

    const styles: Record<string, string> = {};
    for (const [stateKey, stateValue] of Object.entries(nodeState)) {
      const stateValues = textStateConfig[stateKey as keyof typeof textStateConfig];
      if (!stateValues || !(stateValue in stateValues)) continue;
      Object.assign(styles, stateValues[stateValue as keyof typeof stateValues].css);
    }

    if (Object.keys(styles).length === 0) return base;
    return `<span style="${cssToInlineStyle(styles)}">${base}</span>`;
  },
  heading: ({ node, nodesToHTML, providedStyleTag }) => {
    const children = nodesToHTML({ nodes: node.children }).join("");
    const tag = node.tag === "h2" || node.tag === "h3" || node.tag === "h4" ? node.tag : "h2";
    const plain = children.replace(/<[^>]+>/g, "").trim();
    const idAttr =
      tag === "h2" && plain ? ` id="${escapeHtml(slugifyHeading(plain) || "section")}"` : "";
    return `<${tag}${idAttr}${providedStyleTag}>${children}</${tag}>`;
  },
  blocks: {
    [RESEARCH_BLOCK_SLUGS.figure]: ({ node }: { node: { fields: unknown } }) => {
      const fields = node.fields as {
        image?: unknown;
        alt?: string | null;
        caption?: string | null;
      };
      const src = resolveResearchMediaUrl(fields.image as never);
      if (!src) return "";

      const alt = escapeHtml(resolveResearchMediaAlt(fields.image as never, fields.alt));
      const caption = fields.caption?.trim();

      return `<figure class="figure"><img alt="${alt}" loading="lazy" src="${escapeHtml(src)}" />${
        caption ? `<figcaption class="figcaption">${escapeHtml(resolveSiteCopy(caption))}</figcaption>` : ""
      }</figure>`;
    },
    [RESEARCH_BLOCK_SLUGS.callout]: ({ node }: { node: { fields: unknown } }) => {
      const fields = node.fields as { label?: string; body?: string };
      const label = fields.label?.trim();
      const body = fields.body?.trim();
      if (!label || !body) return "";

      return `<div class="content-card"><p><strong>${escapeHtml(resolveSiteCopy(label))}：</strong> ${escapeHtml(resolveSiteCopy(body))}</p></div>`;
    },
    [RESEARCH_BLOCK_SLUGS.lead]: ({ node }: { node: { fields: unknown } }) => {
      const fields = node.fields as { text?: string };
      const text = fields.text?.trim();
      if (!text) return "";
      return `<p class="lead">${escapeHtml(resolveSiteCopy(text))}</p>`;
    },
    [RESEARCH_BLOCK_SLUGS.inlineCta]: ({ node }: { node: { fields: unknown } }) => {
      const fields = node.fields as {
        kicker?: string | null;
        title?: string;
        description?: string;
        buttonLabel?: string;
        buttonHref?: string;
      };
      const title = fields.title?.trim();
      const description = fields.description?.trim();
      const buttonLabel = fields.buttonLabel?.trim() || "开始免费试用";
      const buttonHref = fields.buttonHref?.trim() || "/auth/register";
      if (!title || !description) return "";

      const kicker = fields.kicker?.trim();

      return `<div class="inline-cta" role="complementary"><div class="cta-copy">${
        kicker ? `<span class="cta-kicker">${escapeHtml(resolveSiteCopy(kicker))}</span>` : ""
      }<h2>${escapeHtml(resolveSiteCopy(title))}</h2><p>${escapeHtml(resolveSiteCopy(description))}</p></div><a class="btn-orange" href="${escapeHtml(buttonHref)}">${escapeHtml(resolveSiteCopy(buttonLabel))}</a></div>`;
    },
  },
});

/** 研究报告 Lexical → HTML（含自定义 Block + H2 anchor） */
export function researchRichTextToHtml(content: unknown): string {
  if (!content || typeof content !== "object" || !("root" in content)) return "";

  try {
    const html = convertLexicalToHTML({
      converters: researchHtmlConverters,
      data: content as SerializedEditorState,
      disableContainer: true,
    });
    return resolveSiteCopy(html);
  } catch {
    return "";
  }
}
