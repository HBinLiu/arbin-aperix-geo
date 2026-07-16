import type { Field } from "payload";
import { APP_LINK_KEYS, APP_LINK_OPTIONS } from "@shared/app-links";

export const briefBlockFields: Field[] = [
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
    defaultValue: "简要列表",
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
        label: "要点标题",
      },
      {
        name: "body",
        type: "textarea",
        label: "补充说明",
        validate: (value, { siblingData }) => {
          const body = (typeof value === "string" ? value : "").trim();
          const lead =
            typeof (siblingData as { lead?: string | null } | undefined)?.lead === "string"
              ? (siblingData as { lead: string }).lead.trim()
              : "";
          if (lead || body) return true;
          return "要点标题与补充说明至少填写一项";
        },
      },
    ],
  },
];

export const calloutBlockFields: Field[] = [
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
];

export const chapterBlockFields: Field[] = [
  {
    name: "text",
    type: "textarea",
    required: true,
    label: "导语",
  },
];

export const figureBlockFields: Field[] = [
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
];

export const highlightBlockFields: Field[] = [
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
];

export const infoGridBlockFields: Field[] = [
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
];

export const inlineCtaBlockFields: Field[] = [
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
];
