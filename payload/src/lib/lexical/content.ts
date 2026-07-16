import {
  BlocksFeature,
  EXPERIMENTAL_TableFeature,
  FixedToolbarFeature,
  HeadingFeature,
  lexicalEditor,
  TextStateFeature,
} from "@payloadcms/richtext-lexical";

import { contentLexicalBlocks } from "../../blocks";
import { textStateConfig } from "./default";

/** 正文 richText 编辑器：news / blog / academy / research 共用 */
export const contentLexicalEditor = lexicalEditor({
  features: ({ defaultFeatures }) => {
    const withoutInlineToolbar = defaultFeatures.filter((feature) => feature.key !== "toolbarInline");
    const withoutHeading = withoutInlineToolbar.filter((feature) => feature.key !== "heading");

    return [
      FixedToolbarFeature(),
      ...withoutHeading,
      HeadingFeature({ enabledHeadingSizes: ["h2", "h3", "h4"] }),
      TextStateFeature({ state: textStateConfig }),
      EXPERIMENTAL_TableFeature(),
      BlocksFeature({ blocks: contentLexicalBlocks }),
    ];
  },
});
