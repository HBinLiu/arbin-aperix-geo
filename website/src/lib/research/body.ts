import {
  contentRichTextToHtml,
  createContentHtmlConverters,
  researchContentBodyClasses,
} from "@/lib/content/body";
import { resolveResearchMediaAlt, resolveResearchMediaUrl } from "@/lib/research/media";
import { slugifyHeading } from "@/lib/research/toc";

export const researchHtmlConverters = createContentHtmlConverters({
  classes: researchContentBodyClasses,
  resolveMediaUrl: resolveResearchMediaUrl,
  resolveMediaAlt: resolveResearchMediaAlt,
  slugifyHeading,
});

/** 研究报告 Lexical → HTML */
export function researchRichTextToHtml(content: unknown): string {
  return contentRichTextToHtml(content, researchHtmlConverters);
}
