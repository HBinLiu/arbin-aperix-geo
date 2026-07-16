import type { Block } from "payload";
import { CONTENT_BLOCK_SLUGS } from "@shared/content/blocks";

import { chapterBlockFields } from "../fields";

/** 章节导语 */
export const ChapterBlock: Block = {
  slug: CONTENT_BLOCK_SLUGS.chapter,
  labels: { singular: "章节导语", plural: "章节导语" },
  fields: chapterBlockFields,
};
