import {
  contentRichTextToHtml,
  createContentHtmlConverters,
  prefixedContentBodyClasses,
} from "@/lib/content/body";
import { resolveAcademyMediaAlt, resolveAcademyMediaUrl } from "@/lib/academy/media";
import { slugifyHeading } from "@/lib/academy/toc";

export const academyHtmlConverters = createContentHtmlConverters({
  classes: prefixedContentBodyClasses("academy"),
  resolveMediaUrl: resolveAcademyMediaUrl,
  resolveMediaAlt: resolveAcademyMediaAlt,
  slugifyHeading,
});

/** 学院 Lexical → HTML */
export function academyRichTextToHtml(content: unknown): string {
  return contentRichTextToHtml(content, academyHtmlConverters);
}
