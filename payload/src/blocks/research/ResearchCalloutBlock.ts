import type { Block } from "payload";

/** 高亮框：标签 + 正文（参考 content-card） */
export const ResearchCalloutBlock: Block = {
  slug: "researchCallout",
  labels: { singular: "高亮框", plural: "高亮框" },
  fields: [
    {
      name: "label",
      type: "text",
      required: true,
      label: "标签",
      admin: { description: "如「核心判断」「GEO成熟度模型」" },
    },
    {
      name: "body",
      type: "textarea",
      required: true,
      label: "正文",
    },
  ],
};
