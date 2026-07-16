import type { Block } from "payload";
import { CONTENT_BLOCK_SLUGS } from "@shared/content/blocks";

import { briefBlockFields } from "../fields";

/** 简要列表 */
export const BriefBlock: Block = {
  slug: CONTENT_BLOCK_SLUGS.brief,
  labels: { singular: "简要列表", plural: "简要列表" },
  fields: briefBlockFields,
};
