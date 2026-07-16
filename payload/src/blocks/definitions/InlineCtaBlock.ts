import type { Block } from "payload";
import { CONTENT_BLOCK_SLUGS } from "@shared/content/blocks";

import { inlineCtaBlockFields } from "../fields";

/** 行内 CTA */
export const InlineCtaBlock: Block = {
  slug: CONTENT_BLOCK_SLUGS.inlineCta,
  labels: { singular: "行内 CTA", plural: "行内 CTA" },
  fields: inlineCtaBlockFields,
};
