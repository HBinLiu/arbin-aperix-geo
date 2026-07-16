import type { Block } from "payload";

/** 60 秒简报（参考 .brief） */
export const AcademyBriefBlock: Block = {
  slug: "academyBrief",
  labels: { singular: "60 秒简报", plural: "60 秒简报" },
  fields: [
    {
      name: "anchorId",
      type: "text",
      label: "锚点 ID",
      defaultValue: "brief",
      admin: { description: "目录跳转用，默认 brief" },
    },
    {
      name: "eyebrow",
      type: "text",
      label: "角标",
      defaultValue: "60 秒简报",
    },
    {
      name: "title",
      type: "text",
      required: true,
      label: "标题",
      admin: { description: "如「用 60 秒理解这篇文章」" },
    },
    {
      name: "items",
      type: "array",
      label: "要点",
      minRows: 1,
      required: true,
      fields: [
        {
          name: "lead",
          type: "text",
          required: true,
          label: "要点标题（加粗）",
        },
        {
          name: "body",
          type: "textarea",
          label: "补充说明",
        },
      ],
    },
  ],
};
