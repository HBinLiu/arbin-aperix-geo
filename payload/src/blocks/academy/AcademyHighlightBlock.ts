import type { Block } from "payload";

/** 高亮框：标签 + 正文 */
export const AcademyHighlightBlock: Block = {
  slug: "academyHighlight",
  labels: { singular: "高亮框", plural: "高亮框" },
  fields: [
    {
      name: "label",
      type: "text",
      required: true,
      label: "标签",
      admin: { description: "如「核心判断」「关键信号」" },
    },
    {
      name: "body",
      type: "textarea",
      required: true,
      label: "正文",
    },
  ],
};
