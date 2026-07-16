import {
  contentRichTextToHtml,
  createContentHtmlConverters,
  prefixedContentBodyClasses,
} from "@/lib/content/body";
import { resolveChangelogMediaAlt, resolveChangelogMediaUrl } from "@/lib/changelog/media";
import { slugifyHeading } from "@/lib/changelog/toc";

export const changelogHtmlConverters = createContentHtmlConverters({
  classes: prefixedContentBodyClasses("changelog"),
  resolveMediaUrl: resolveChangelogMediaUrl,
  resolveMediaAlt: resolveChangelogMediaAlt,
  slugifyHeading,
});

/** 更新日志 Lexical → HTML */
export function changelogRichTextToHtml(content: unknown): string {
  return contentRichTextToHtml(content, changelogHtmlConverters);
}
