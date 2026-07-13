import type { Block } from "payload";

/** 插入图片：Media 上传 + 说明 */
export const NewsFigureBlock: Block = {
  slug: "newsFigure",
  labels: { singular: "插入图片", plural: "插入图片" },
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
