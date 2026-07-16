import type { Block } from "payload";
import { CONTENT_BLOCK_SLUGS } from "@shared/content/blocks";

import { infoGridBlockFields } from "../fields";

/** 双栏信息卡 */
export const InfoGridBlock: Block = {
  slug: CONTENT_BLOCK_SLUGS.infoGrid,
  labels: { singular: "双栏信息卡", plural: "双栏信息卡" },
  fields: infoGridBlockFields,
};
