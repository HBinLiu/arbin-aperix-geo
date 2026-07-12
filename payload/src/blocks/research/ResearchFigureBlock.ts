import type { Block } from "payload";

/** 图表：Media 图片 + 说明 */
export const ResearchFigureBlock: Block = {
  slug: "researchFigure",
  labels: { singular: "图表", plural: "图表" },
  fields: [
    {
      name: "image",
      type: "upload",
      relationTo: "media",
      required: true,
      label: "图片",
    },
    {
      name: "alt",
      type: "text",
      label: "Alt 文本",
    },
    {
      name: "caption",
      type: "textarea",
      label: "图注",
    },
  ],
};
