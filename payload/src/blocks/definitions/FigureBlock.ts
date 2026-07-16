import type { Block } from "payload";
import { CONTENT_BLOCK_SLUGS } from "@shared/content/blocks";

import { figureBlockFields } from "../fields";

/** 插入图片 */
export const FigureBlock: Block = {
  slug: CONTENT_BLOCK_SLUGS.figure,
  labels: { singular: "插入图片", plural: "插入图片" },
  fields: figureBlockFields,
};
