import type { Block } from "payload";

/** 双栏信息卡区块：外围容器 + 标题/段落 + 双栏卡片（参考 .grid-two + .info-card） */
export const AcademyInfoGridBlock: Block = {
  slug: "academyInfoGrid",
  labels: { singular: "双栏信息卡", plural: "双栏信息卡" },
  fields: [
    {
      name: "anchorId",
      type: "text",
      label: "锚点 ID",
      admin: { description: "目录跳转用，留空则按标题自动生成" },
    },
    {
      name: "title",
      type: "text",
      label: "区块标题",
      admin: {
        description: "可选；填写后渲染为 H2 并显示外围容器。仅填卡片时不显示外围区域",
      },
    },
    {
      name: "paragraphs",
      type: "array",
      label: "说明段落",
      admin: { description: "标题与卡片之间的正文" },
      fields: [
        {
          name: "text",
          type: "textarea",
          required: true,
          label: "内容",
        },
      ],
    },
    {
      name: "cards",
      type: "array",
      label: "卡片",
      minRows: 2,
      maxRows: 4,
      required: true,
      admin: { description: "至少 2 张；桌面端两列排列，移动端单列" },
      fields: [
        {
          name: "label",
          type: "text",
          label: "角标",
          admin: { description: "如 LAYER 01、01" },
        },
        {
          name: "title",
          type: "text",
          required: true,
          label: "标题",
        },
        {
          name: "description",
          type: "textarea",
          label: "说明",
        },
      ],
    },
  ],
};
