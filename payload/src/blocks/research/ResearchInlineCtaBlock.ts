import type { Block } from "payload";
import { APP_LINK_KEYS, APP_LINK_OPTIONS } from "@shared/app-links";

/** 行内 CTA（参考 inline-cta） */
export const ResearchInlineCtaBlock: Block = {
  slug: "researchInlineCta",
  labels: { singular: "行内 CTA", plural: "行内 CTA" },
  fields: [
    {
      name: "kicker",
      type: "text",
      label: "角标",
      admin: { description: "如「体验 {{siteName}}」，可留空" },
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
      required: true,
      label: "描述",
    },
    {
      name: "buttonLabel",
      type: "text",
      required: true,
      label: "按钮文案",
      defaultValue: "开始免费试用",
    },
    {
      name: "buttonHref",
      type: "select",
      required: true,
      label: "按钮链接",
      defaultValue: APP_LINK_KEYS.register,
      options: APP_LINK_OPTIONS,
      admin: {
        description: "实际 URL 由官网环境变量 PUBLIC_REGISTER_URL / PUBLIC_LOGIN_URL 配置",
      },
    },
  ],
};
