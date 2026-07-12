import {
  defaultColors,
  EXPERIMENTAL_TableFeature,
  FixedToolbarFeature,
  HeadingFeature,
  lexicalEditor,
  TextStateFeature,
} from "@payloadcms/richtext-lexical";

/** TextStateFeature 配置（website/src/lib/lexical.ts 需保持同步） */
export const textStateConfig = {
  color: {
    ...defaultColors.text,
    ...defaultColors.background,
  },
} as const;

/** 顶部固定工具栏；保留 Payload 默认能力，去掉浮动条避免重复 */
export const defaultLexicalEditor = lexicalEditor({
  features: ({ defaultFeatures }) => {
    const withoutInlineToolbar = defaultFeatures.filter((feature) => feature.key !== "toolbarInline");
    const withoutHeading = withoutInlineToolbar.filter((feature) => feature.key !== "heading");

    return [
      FixedToolbarFeature(),
      ...withoutHeading,
      HeadingFeature({ enabledHeadingSizes: ["h2", "h3", "h4"] }),
      TextStateFeature({ state: textStateConfig }),
      EXPERIMENTAL_TableFeature(),
    ];
  },
});
