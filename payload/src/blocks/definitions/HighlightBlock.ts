import type { Block } from "payload";
import { CONTENT_BLOCK_SLUGS } from "@shared/content/blocks";

import { highlightBlockFields } from "../fields";

/** 高亮框（label + body） */
export const HighlightBlock: Block = {
  slug: CONTENT_BLOCK_SLUGS.highlight,
  labels: { singular: "高亮框", plural: "高亮框" },
  fields: highlightBlockFields,
};
