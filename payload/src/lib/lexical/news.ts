import {
  BlocksFeature,
  EXPERIMENTAL_TableFeature,
  FixedToolbarFeature,
  HeadingFeature,
  lexicalEditor,
  TextStateFeature,
} from "@payloadcms/richtext-lexical";

import { newsLexicalBlocks } from "../../blocks/news";
import { textStateConfig } from "./default";

/** 新闻正文编辑器（独立于 research） */
export const newsLexicalEditor = lexicalEditor({
  features: ({ defaultFeatures }) => {
    const withoutInlineToolbar = defaultFeatures.filter((feature) => feature.key !== "toolbarInline");
    const withoutHeading = withoutInlineToolbar.filter((feature) => feature.key !== "heading");

    return [
      FixedToolbarFeature(),
      ...withoutHeading,
      HeadingFeature({ enabledHeadingSizes: ["h2", "h3", "h4"] }),
      TextStateFeature({ state: textStateConfig }),
      EXPERIMENTAL_TableFeature(),
      BlocksFeature({ blocks: newsLexicalBlocks }),
    ];
  },
});
