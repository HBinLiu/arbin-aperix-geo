import {
  contentRichTextToHtml,
  createContentHtmlConverters,
  prefixedContentBodyClasses,
} from "@/lib/content/body";
import { resolveBlogMediaAlt, resolveBlogMediaUrl } from "@/lib/blog/media";
import { slugifyHeading } from "@/lib/blog/toc";

export const blogHtmlConverters = createContentHtmlConverters({
  classes: prefixedContentBodyClasses("blog"),
  resolveMediaUrl: resolveBlogMediaUrl,
  resolveMediaAlt: resolveBlogMediaAlt,
  slugifyHeading,
});

/** 博客 Lexical → HTML */
export function blogRichTextToHtml(content: unknown): string {
  return contentRichTextToHtml(content, blogHtmlConverters);
}
