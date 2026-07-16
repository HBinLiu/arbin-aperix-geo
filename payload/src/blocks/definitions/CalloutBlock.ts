import type { Block } from "payload";
import { CONTENT_BLOCK_SLUGS } from "@shared/content/blocks";

import { calloutBlockFields } from "../fields";

/** 引用框（lead + body） */
export const CalloutBlock: Block = {
  slug: CONTENT_BLOCK_SLUGS.callout,
  labels: { singular: "引用框", plural: "引用框" },
  fields: calloutBlockFields,
};
