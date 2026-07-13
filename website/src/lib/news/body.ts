import {
  NEWS_BLOCK_SLUGS,
  type NewsBriefBlockFields,
  type NewsCalloutBlockFields,
  type NewsFigureBlockFields,
  type NewsHighlightBlockFields,
  type NewsInfoGridBlockFields,
  type NewsInlineCtaBlockFields,
  type NewsLeadBlockFields,
} from "@shared/news/blocks";
import type { HTMLConvertersFunction } from "@payloadcms/richtext-lexical/html";
import { convertLexicalToHTML } from "@payloadcms/richtext-lexical/html";
import { defaultColors } from "@payloadcms/richtext-lexical/defaultColors";
import type { SerializedEditorState, SerializedTextNode } from "lexical";

import { resolveNewsMediaAlt, resolveNewsMediaUrl } from "@/lib/news/media";
import { slugifyHeading } from "@/lib/news/toc";
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

function sanitizeAnchorId(value: string | null | undefined, fallback: string): string {
  const raw = value?.trim() || fallback;
  const sanitized = raw
    .toLowerCase()
    .replace(/[^a-z0-9_-]/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
  return sanitized || fallback;
}

export const newsHtmlConverters: HTMLConvertersFunction = ({ defaultConverters }) => ({
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
  paragraph: (args) => {
    const { node, nodesToHTML, parent, providedStyleTag } = args;
    const children = nodesToHTML({ nodes: node.children });

    if (parent?.type === "tablecell") {
      return children.join("") || "";
    }

    if (typeof defaultConverters.paragraph === "function") {
      return defaultConverters.paragraph(args);
    }

    const inner = children.join("");
    if (!inner) {
      return `<p${providedStyleTag}> </p>`;
    }
    return `<p${providedStyleTag}>${inner}</p>`;
  },
  table: ({ node, nodesToHTML }) => {
    const children = nodesToHTML({ nodes: node.children }).join("");
    return `<div class="news-table-wrap"><table class="news-table">${children}</table></div>`;
  },
  tablerow: ({ node, nodesToHTML }) => {
    const children = nodesToHTML({ nodes: node.children }).join("");
    return `<tr>${children}</tr>`;
  },
  tablecell: ({ node, nodesToHTML }) => {
    const children = nodesToHTML({ nodes: node.children }).join("");
    const tag = node.headerState > 0 ? "th" : "td";
    return `<${tag}>${children}</${tag}>`;
  },
  blocks: {
    [NEWS_BLOCK_SLUGS.brief]: ({ node }: { node: { fields: unknown } }) => {
      const fields = node.fields as NewsBriefBlockFields;
      const title = fields.title?.trim();
      if (!title || !fields.items?.length) return "";

      const anchorId = sanitizeAnchorId(fields.anchorId, "brief");
      const eyebrow = fields.eyebrow?.trim() || "60 秒简报";
      const itemsHtml = fields.items
        .map((item) => {
          const lead = item.lead?.trim();
          if (!lead) return "";
          const body = item.body?.trim();
          const bodyHtml = body ? ` ${escapeHtml(resolveSiteCopy(body))}` : "";
          return `<li><strong>${escapeHtml(resolveSiteCopy(lead))}</strong>${bodyHtml}</li>`;
        })
        .filter(Boolean)
        .join("");

      if (!itemsHtml) return "";

      return `<section class="news-brief" id="${escapeHtml(anchorId)}"><span class="news-eyebrow">${escapeHtml(resolveSiteCopy(eyebrow))}</span><h2>${escapeHtml(resolveSiteCopy(title))}</h2><ul>${itemsHtml}</ul></section>`;
    },
    [NEWS_BLOCK_SLUGS.callout]: ({ node }: { node: { fields: unknown } }) => {
      const fields = node.fields as NewsCalloutBlockFields;
      const lead = fields.lead?.trim();
      if (!lead) return "";

      const body = fields.body?.trim();
      const bodyHtml = body ? ` ${escapeHtml(resolveSiteCopy(body))}` : "";

      return `<div class="news-callout"><p><strong>${escapeHtml(resolveSiteCopy(lead))}</strong>${bodyHtml}</p></div>`;
    },
    [NEWS_BLOCK_SLUGS.figure]: ({ node }: { node: { fields: unknown } }) => {
      const fields = node.fields as NewsFigureBlockFields;
      const src = resolveNewsMediaUrl(fields.image);
      if (!src) return "";

      const alt = escapeHtml(resolveNewsMediaAlt(fields.image, fields.alt));
      const caption = fields.caption?.trim();

      return `<figure class="news-figure"><img alt="${alt}" loading="lazy" src="${escapeHtml(src)}" />${
        caption ? `<figcaption class="news-figcaption">${escapeHtml(resolveSiteCopy(caption))}</figcaption>` : ""
      }</figure>`;
    },
    [NEWS_BLOCK_SLUGS.highlight]: ({ node }: { node: { fields: unknown } }) => {
      const fields = node.fields as NewsHighlightBlockFields;
      const label = fields.label?.trim();
      const body = fields.body?.trim();
      if (!label || !body) return "";

      return `<div class="news-highlight"><p><strong>${escapeHtml(resolveSiteCopy(label))}：</strong> ${escapeHtml(resolveSiteCopy(body))}</p></div>`;
    },
    [NEWS_BLOCK_SLUGS.infoGrid]: ({ node }: { node: { fields: unknown } }) => {
      const fields = node.fields as NewsInfoGridBlockFields;
      const title = fields.title?.trim();
      const cards = fields.cards?.filter((card) => card.title?.trim()) ?? [];
      if (cards.length < 2) return "";

      const paragraphsHtml = (fields.paragraphs ?? [])
        .map((paragraph) => {
          const text = paragraph.text?.trim();
          if (!text) return "";
          return `<p class="news-info-section-p">${escapeHtml(resolveSiteCopy(text))}</p>`;
        })
        .filter(Boolean)
        .join("");

      const cardsHtml = cards
        .map((card) => {
          const label = card.label?.trim();
          const labelHtml = label
            ? `<small>${escapeHtml(resolveSiteCopy(label))}</small>`
            : "";
          const description = card.description?.trim();
          const descriptionHtml = description
            ? `<p>${escapeHtml(resolveSiteCopy(description))}</p>`
            : "";
          return `<div class="news-info-card">${labelHtml}<h3>${escapeHtml(resolveSiteCopy(card.title))}</h3>${descriptionHtml}</div>`;
        })
        .join("");

      const gridHtml = `<div class="news-grid-two">${cardsHtml}</div>`;
      if (!title && !paragraphsHtml) return gridHtml;

      const anchorId = sanitizeAnchorId(
        fields.anchorId,
        title ? slugifyHeading(title) : "info-section",
      );
      const idAttr =
        title || fields.anchorId?.trim() ? ` id="${escapeHtml(anchorId)}"` : "";
      const titleHtml = title ? `<h2>${escapeHtml(resolveSiteCopy(title))}</h2>` : "";

      return `<section class="news-info-section"${idAttr}>${titleHtml}${paragraphsHtml}${gridHtml}</section>`;
    },
    [NEWS_BLOCK_SLUGS.lead]: ({ node }: { node: { fields: unknown } }) => {
      const fields = node.fields as NewsLeadBlockFields;
      const text = fields.text?.trim();
      if (!text) return "";
      return `<p class="news-lead">${escapeHtml(resolveSiteCopy(text))}</p>`;
    },
    [NEWS_BLOCK_SLUGS.inlineCta]: ({ node }: { node: { fields: unknown } }) => {
      const fields = node.fields as NewsInlineCtaBlockFields;
      const title = fields.title?.trim();
      const description = fields.description?.trim();
      const buttonLabel = fields.buttonLabel?.trim() || "开始免费试用";
      const buttonHref = fields.buttonHref?.trim() || "/auth/register";
      if (!title || !description) return "";

      const kicker = fields.kicker?.trim();

      return `<div class="news-inline-cta" role="complementary"><div class="news-inline-cta-copy">${
        kicker ? `<span class="news-cta-kicker">${escapeHtml(resolveSiteCopy(kicker))}</span>` : ""
      }<h2>${escapeHtml(resolveSiteCopy(title))}</h2><p>${escapeHtml(resolveSiteCopy(description))}</p></div><a class="news-btn-primary" href="${escapeHtml(buttonHref)}">${escapeHtml(resolveSiteCopy(buttonLabel))}</a></div>`;
    },
  },
});

/** 新闻 Lexical → HTML（独立 converter，不依赖 research） */
export function newsRichTextToHtml(content: unknown): string {
  if (!content || typeof content !== "object" || !("root" in content)) return "";

  try {
    const html = convertLexicalToHTML({
      converters: newsHtmlConverters,
      data: content as SerializedEditorState,
      disableContainer: true,
    });
    return resolveSiteCopy(html);
  } catch {
    return "";
  }
}
