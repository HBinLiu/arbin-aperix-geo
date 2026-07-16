import {
  contentRichTextToHtml,
  createContentHtmlConverters,
  prefixedContentBodyClasses,
} from "@/lib/content/body";
import { resolveNewsMediaAlt, resolveNewsMediaUrl } from "@/lib/news/media";
import { slugifyHeading } from "@/lib/news/toc";

export const newsHtmlConverters = createContentHtmlConverters({
  classes: prefixedContentBodyClasses("news"),
  resolveMediaUrl: resolveNewsMediaUrl,
  resolveMediaAlt: resolveNewsMediaAlt,
  slugifyHeading,
});

/** 新闻 Lexical → HTML */
export function newsRichTextToHtml(content: unknown): string {
  return contentRichTextToHtml(content, newsHtmlConverters);
}
