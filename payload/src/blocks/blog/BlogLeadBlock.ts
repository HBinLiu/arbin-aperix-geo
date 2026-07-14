import type { Block } from "payload";

/** 章节导语 */
export const BlogLeadBlock: Block = {
  slug: "blogLead",
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
