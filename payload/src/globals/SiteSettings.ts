import type { GlobalConfig } from "payload";

export const SiteSettings: GlobalConfig = {
  slug: "site-settings",
  label: "站点设置",
  fields: [
    {
      name: "siteName",
      type: "text",
      label: "站点名称",
      required: true,
      defaultValue: "Aperix AI",
    },
    {
      name: "siteDescription",
      type: "textarea",
      label: "站点描述",
      admin: {
        description: "用于页头品牌区展示（可选）",
      },
    },
    {
      name: "seo",
      type: "group",
      label: "默认 SEO",
      fields: [
        { name: "title", type: "text", label: "页面标题", required: true },
        { name: "description", type: "textarea", label: "页面描述", required: true },
      ],
    },
  ],
};
