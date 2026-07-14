import {
  BlocksFeature,
  EXPERIMENTAL_TableFeature,
  FixedToolbarFeature,
  HeadingFeature,
  lexicalEditor,
  TextStateFeature,
} from "@payloadcms/richtext-lexical";

import { blogLexicalBlocks } from "../../blocks/blog";
import { textStateConfig } from "./default";

/** 博客正文编辑器（独立 blocks） */
export const blogLexicalEditor = lexicalEditor({
  features: ({ defaultFeatures }) => {
    const withoutInlineToolbar = defaultFeatures.filter((feature) => feature.key !== "toolbarInline");
    const withoutHeading = withoutInlineToolbar.filter((feature) => feature.key !== "heading");

    return [
      FixedToolbarFeature(),
      ...withoutHeading,
      HeadingFeature({ enabledHeadingSizes: ["h2", "h3", "h4"] }),
      TextStateFeature({ state: textStateConfig }),
      EXPERIMENTAL_TableFeature(),
      BlocksFeature({ blocks: blogLexicalBlocks }),
    ];
  },
});
