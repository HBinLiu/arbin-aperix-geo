import type { Block } from "payload";

/** 章节导语（参考 p.lead） */
export const ResearchLeadBlock: Block = {
  slug: "researchLead",
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
