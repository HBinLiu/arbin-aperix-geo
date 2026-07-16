import type { Block } from "payload";

/** 引用框（参考 .callout，区别于研究报告「高亮框」） */
export const AcademyCalloutBlock: Block = {
  slug: "academyCallout",
  labels: { singular: "引用框", plural: "引用框" },
  fields: [
    {
      name: "lead",
      type: "text",
      required: true,
      label: "加粗句",
      admin: { description: "段落开头加粗部分" },
    },
    {
      name: "body",
      type: "textarea",
      label: "后续说明",
      admin: { description: "加粗句后的正文，可留空" },
    },
  ],
};
