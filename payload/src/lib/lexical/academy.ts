import {
  BlocksFeature,
  EXPERIMENTAL_TableFeature,
  FixedToolbarFeature,
  HeadingFeature,
  lexicalEditor,
  TextStateFeature,
} from "@payloadcms/richtext-lexical";

import { academyLexicalBlocks } from "../../blocks/academy";
import { textStateConfig } from "./default";

/** 学院正文编辑器（独立于 news / blog） */
export const academyLexicalEditor = lexicalEditor({
  features: ({ defaultFeatures }) => {
    const withoutInlineToolbar = defaultFeatures.filter((feature) => feature.key !== "toolbarInline");
    const withoutHeading = withoutInlineToolbar.filter((feature) => feature.key !== "heading");

    return [
      FixedToolbarFeature(),
      ...withoutHeading,
      HeadingFeature({ enabledHeadingSizes: ["h2", "h3", "h4"] }),
      TextStateFeature({ state: textStateConfig }),
      EXPERIMENTAL_TableFeature(),
      BlocksFeature({ blocks: academyLexicalBlocks }),
    ];
  },
});
