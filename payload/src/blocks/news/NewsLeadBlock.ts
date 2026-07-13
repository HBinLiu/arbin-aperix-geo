import type { Block } from "payload";

/** 章节导语 */
export const NewsLeadBlock: Block = {
  slug: "newsLead",
  labels: { singular: "章节导语", plural: "章节导语" },
  fields: [
    {
      name: "text",
      type: "textarea",
      required: true,
      label: "导语",
    },
  ],
};
