import type { CollectionConfig } from "payload";

export const Pages: CollectionConfig = {
  slug: "pages",
  admin: {
    useAsTitle: "title",
    defaultColumns: ["title", "slug", "status", "updatedAt"],
  },
  versions: {
    drafts: true,
  },
  fields: [
    {
      name: "title",
      type: "text",
      required: true,
    },
    {
      name: "slug",
      type: "text",
      required: true,
      unique: true,
      admin: {
        description: "首页填 home；定价页 pricing；关于 about",
      },
    },
    {
      name: "status",
      type: "select",
      required: true,
      defaultValue: "draft",
      options: [
        { label: "草稿", value: "draft" },
        { label: "已发布", value: "published" },
      ],
    },
    {
      name: "seo",
      type: "group",
      fields: [
        { name: "title", type: "text" },
        { name: "description", type: "textarea" },
      ],
    },
    {
      name: "hero",
      type: "group",
      fields: [
        { name: "eyebrow", type: "text", label: "顶标" },
        { name: "headline", type: "text", label: "主标题", required: true },
        { name: "headlineAccent", type: "text", label: "主标题强调行" },
        { name: "description", type: "textarea", label: "副文案" },
        { name: "primaryCtaLabel", type: "text", label: "主按钮文案", defaultValue: "免费注册" },
        { name: "primaryCtaHref", type: "text", label: "主按钮链接", defaultValue: "/auth/register" },
      ],
    },
    {
      name: "workflow",
      type: "group",
      label: "三步闭环",
      fields: [
        { name: "title", type: "text", label: "区块标题" },
        { name: "description", type: "textarea", label: "区块说明" },
        {
          name: "steps",
          type: "array",
          fields: [
            { name: "step", type: "text", label: "序号", required: true },
            { name: "title", type: "text", label: "标题", required: true },
            { name: "description", type: "textarea", label: "说明", required: true },
          ],
        },
      ],
    },
    {
      name: "painPoints",
      type: "array",
      label: "痛点与方案",
      fields: [
        { name: "pain", type: "textarea", label: "痛点", required: true },
        { name: "solution", type: "textarea", label: "方案", required: true },
      ],
    },
    {
      name: "stats",
      type: "array",
      label: "数字条",
      fields: [
        { name: "label", type: "text", label: "标签", required: true },
        { name: "value", type: "text", label: "数值", required: true },
        { name: "description", type: "text", label: "说明", required: true },
      ],
    },
    {
      name: "cta",
      type: "group",
      label: "底部 CTA",
      fields: [
        { name: "title", type: "text", label: "标题" },
        { name: "description", type: "textarea", label: "说明" },
        { name: "primaryCtaLabel", type: "text", label: "主按钮" },
        { name: "primaryCtaHref", type: "text", label: "主按钮链接" },
      ],
    },
  ],
};
