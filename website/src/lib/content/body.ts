import {
  CONTENT_BLOCK_SLUGS,
  type BriefBlockFields,
  type CalloutBlockFields,
  type FigureBlockFields,
  type HighlightBlockFields,
  type InfoGridBlockFields,
  type InlineCtaBlockFields,
  type ChapterBlockFields,
} from "@shared/content/blocks";
import type { HTMLConvertersFunction } from "@payloadcms/richtext-lexical/html";
import { convertLexicalToHTML } from "@payloadcms/richtext-lexical/html";
import { defaultColors } from "@payloadcms/richtext-lexical/defaultColors";
import type { SerializedEditorState, SerializedTextNode } from "lexical";

import { resolveAppLink } from "@/lib/app-links";
import { resolveSiteCopy } from "@/lib/site";

const textStateConfig = {
  color: {
    ...defaultColors.text,
    ...defaultColors.background,
  },
} as const;

const NODE_STATE_KEY = "$";

export type ContentBodyClasses = {
  tableWrap: string;
  table: string;
  brief: string;
  eyebrow: string;
  callout: string;
  figure: string;
  figcaption: string;
  highlight: string;
  infoSection: string;
  infoSectionP: string;
  infoCard: string;
  gridTwo: string;
  lead: string;
  inlineCta: string;
  inlineCtaCopy: string;
  ctaKicker: string;
  btnPrimary: string;
};

export type ContentBodyMediaResolver = {
  resolveMediaUrl: (image: FigureBlockFields["image"]) => string | null;
  resolveMediaAlt: (image: FigureBlockFields["image"], alt?: string | null) => string;
};

export type CreateContentHtmlConvertersOptions = ContentBodyMediaResolver & {
  classes: ContentBodyClasses;
  slugifyHeading: (text: string) => string;
};

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

export function prefixedContentBodyClasses(prefix: string): ContentBodyClasses {
  return {
    tableWrap: `${prefix}-table-wrap`,
    table: `${prefix}-table`,
    brief: `${prefix}-brief`,
    eyebrow: `${prefix}-eyebrow`,
    callout: `${prefix}-callout`,
    figure: `${prefix}-figure`,
    figcaption: `${prefix}-figcaption`,
    highlight: `${prefix}-highlight`,
    infoSection: `${prefix}-info-section`,
    infoSectionP: `${prefix}-info-section-p`,
    infoCard: `${prefix}-info-card`,
    gridTwo: `${prefix}-grid-two`,
    lead: `${prefix}-lead`,
    inlineCta: `${prefix}-inline-cta`,
    inlineCtaCopy: `${prefix}-inline-cta-copy`,
    ctaKicker: `${prefix}-cta-kicker`,
    btnPrimary: `${prefix}-btn-primary`,
  };
}

export const researchContentBodyClasses: ContentBodyClasses = {
  tableWrap: "research-table-wrap",
  table: "research-table",
  brief: "brief",
  eyebrow: "eyebrow",
  callout: "callout",
  figure: "figure",
  figcaption: "figcaption",
  highlight: "content-card",
  infoSection: "info-section",
  infoSectionP: "info-section-p",
  infoCard: "info-card",
  gridTwo: "grid-two",
  lead: "lead",
  inlineCta: "inline-cta",
  inlineCtaCopy: "cta-copy",
  ctaKicker: "cta-kicker",
  btnPrimary: "btn-orange",
};

export function createContentHtmlConverters({
  classes,
  resolveMediaUrl,
  resolveMediaAlt,
  slugifyHeading,
}: CreateContentHtmlConvertersOptions): HTMLConvertersFunction {
  const canonicalBlocks = {
    [CONTENT_BLOCK_SLUGS.brief]: ({ node }: { node: { fields: unknown } }) => {
      const fields = node.fields as BriefBlockFields;
      const title = fields.title?.trim();
      if (!title || !fields.items?.length) return "";

      const anchorId = sanitizeAnchorId(fields.anchorId, "brief");
      const eyebrow = fields.eyebrow?.trim() || "简要列表";
      const itemsHtml = fields.items
        .map((item) => {
          const lead = item.lead?.trim();
          const body = item.body?.trim();
          if (!lead && !body) return "";

          if (lead && body) {
            return `<li><strong>${escapeHtml(resolveSiteCopy(lead))}</strong> ${escapeHtml(resolveSiteCopy(body))}</li>`;
          }
          if (lead) {
            return `<li><strong>${escapeHtml(resolveSiteCopy(lead))}</strong></li>`;
          }
          return `<li>${escapeHtml(resolveSiteCopy(body ?? ""))}</li>`;
        })
        .filter(Boolean)
        .join("");

      if (!itemsHtml) return "";

      return `<section class="${classes.brief}" id="${escapeHtml(anchorId)}"><span class="${classes.eyebrow}">${escapeHtml(resolveSiteCopy(eyebrow))}</span><h2>${escapeHtml(resolveSiteCopy(title))}</h2><ul>${itemsHtml}</ul></section>`;
    },
    [CONTENT_BLOCK_SLUGS.callout]: ({ node }: { node: { fields: unknown } }) => {
      const fields = node.fields as CalloutBlockFields;
      const lead = fields.lead?.trim();
      if (!lead) return "";

      const body = fields.body?.trim();
      const bodyHtml = body ? ` ${escapeHtml(resolveSiteCopy(body))}` : "";

      return `<div class="${classes.callout}"><p><strong>${escapeHtml(resolveSiteCopy(lead))}</strong>${bodyHtml}</p></div>`;
    },
    [CONTENT_BLOCK_SLUGS.figure]: ({ node }: { node: { fields: unknown } }) => {
      const fields = node.fields as FigureBlockFields;
      const src = resolveMediaUrl(fields.image);
      if (!src) return "";

      const alt = escapeHtml(resolveMediaAlt(fields.image, fields.alt));
      const caption = fields.caption?.trim();

      return `<figure class="${classes.figure}"><img alt="${alt}" loading="lazy" src="${escapeHtml(src)}" />${
        caption
          ? `<figcaption class="${classes.figcaption}">${escapeHtml(resolveSiteCopy(caption))}</figcaption>`
          : ""
      }</figure>`;
    },
    [CONTENT_BLOCK_SLUGS.highlight]: ({ node }: { node: { fields: unknown } }) => {
      const fields = node.fields as HighlightBlockFields;
      const label = fields.label?.trim();
      const body = fields.body?.trim();
      if (!label || !body) return "";

      return `<div class="${classes.highlight}"><p><strong>${escapeHtml(resolveSiteCopy(label))}：</strong> ${escapeHtml(resolveSiteCopy(body))}</p></div>`;
    },
    [CONTENT_BLOCK_SLUGS.infoGrid]: ({ node }: { node: { fields: unknown } }) => {
      const fields = node.fields as InfoGridBlockFields;
      const title = fields.title?.trim();
      const cards = fields.cards?.filter((card) => card.title?.trim()) ?? [];
      if (cards.length < 2) return "";

      const paragraphsHtml = (fields.paragraphs ?? [])
        .map((paragraph) => {
          const text = paragraph.text?.trim();
          if (!text) return "";
          return `<p class="${classes.infoSectionP}">${escapeHtml(resolveSiteCopy(text))}</p>`;
        })
        .filter(Boolean)
        .join("");

      const cardsHtml = cards
        .map((card) => {
          const label = card.label?.trim();
          const labelHtml = label ? `<small>${escapeHtml(resolveSiteCopy(label))}</small>` : "";
          const description = card.description?.trim();
          const descriptionHtml = description
            ? `<p>${escapeHtml(resolveSiteCopy(description))}</p>`
            : "";
          return `<div class="${classes.infoCard}">${labelHtml}<h3>${escapeHtml(resolveSiteCopy(card.title))}</h3>${descriptionHtml}</div>`;
        })
        .join("");

      const gridHtml = `<div class="${classes.gridTwo}">${cardsHtml}</div>`;
      if (!title && !paragraphsHtml) return gridHtml;

      const anchorId = sanitizeAnchorId(
        fields.anchorId,
        title ? slugifyHeading(title) : "info-section",
      );
      const idAttr = title || fields.anchorId?.trim() ? ` id="${escapeHtml(anchorId)}"` : "";
      const titleHtml = title ? `<h2>${escapeHtml(resolveSiteCopy(title))}</h2>` : "";

      return `<section class="${classes.infoSection}"${idAttr}>${titleHtml}${paragraphsHtml}${gridHtml}</section>`;
    },
    [CONTENT_BLOCK_SLUGS.chapter]: ({ node }: { node: { fields: unknown } }) => {
      const fields = node.fields as ChapterBlockFields;
      const text = fields.text?.trim();
      if (!text) return "";
      return `<p class="${classes.lead}">${escapeHtml(resolveSiteCopy(text))}</p>`;
    },
    [CONTENT_BLOCK_SLUGS.inlineCta]: ({ node }: { node: { fields: unknown } }) => {
      const fields = node.fields as InlineCtaBlockFields;
      const title = fields.title?.trim();
      const description = fields.description?.trim();
      const buttonLabel = fields.buttonLabel?.trim() || "开始注册试用";
      const buttonHref = resolveAppLink(fields.buttonHref);
      if (!title || !description) return "";

      const kicker = fields.kicker?.trim();

      return `<div class="${classes.inlineCta}" role="complementary"><div class="${classes.inlineCtaCopy}">${
        kicker ? `<span class="${classes.ctaKicker}">${escapeHtml(resolveSiteCopy(kicker))}</span>` : ""
      }<h2>${escapeHtml(resolveSiteCopy(title))}</h2><p>${escapeHtml(resolveSiteCopy(description))}</p></div><a class="${classes.btnPrimary}" href="${escapeHtml(buttonHref)}">${escapeHtml(resolveSiteCopy(buttonLabel))}</a></div>`;
    },
  };

  return ({ defaultConverters }) => ({
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
      return `<div class="${classes.tableWrap}"><table class="${classes.table}">${children}</table></div>`;
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
    blocks: canonicalBlocks,
  });
}

export function contentRichTextToHtml(
  content: unknown,
  converters: HTMLConvertersFunction,
): string {
  if (!content || typeof content !== "object" || !("root" in content)) return "";

  try {
    const html = convertLexicalToHTML({
      converters,
      data: content as SerializedEditorState,
      disableContainer: true,
    });
    return resolveSiteCopy(html);
  } catch {
    return "";
  }
}
