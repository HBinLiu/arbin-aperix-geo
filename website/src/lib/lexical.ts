import type { HTMLConvertersFunction } from "@payloadcms/richtext-lexical/html";
import { convertLexicalToHTML } from "@payloadcms/richtext-lexical/html";
import { defaultColors } from "@payloadcms/richtext-lexical/defaultColors";
import type { SerializedEditorState, SerializedTextNode } from "lexical";

import { resolveSiteCopy } from "@/lib/site";

/** 与 payload/src/lib/lexical.ts 中 textStateConfig 保持一致 */
const textStateConfig = {
  color: {
    ...defaultColors.text,
    ...defaultColors.background,
  },
} as const;

const NODE_STATE_KEY = "$";

function cssToInlineStyle(css: Record<string, string>): string {
  return Object.entries(css)
    .map(([property, value]) => `${property}:${value}`)
    .join(";");
}

const htmlConverters: HTMLConvertersFunction = ({ defaultConverters }) => ({
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

      const css = stateValues[stateValue as keyof typeof stateValues].css;
      Object.assign(styles, css);
    }

    if (Object.keys(styles).length === 0) return base;
    return `<span style="${cssToInlineStyle(styles)}">${base}</span>`;
  },
});

/** CMS Lexical JSON → HTML（官网表现层唯一转换入口） */
export function richTextToHtml(content: unknown): string {
  if (!content || typeof content !== "object" || !("root" in content)) return "";

  try {
    const html = convertLexicalToHTML({
      converters: htmlConverters,
      data: content as SerializedEditorState,
      disableContainer: true,
    });
    return resolveSiteCopy(html);
  } catch {
    return "";
  }
}
