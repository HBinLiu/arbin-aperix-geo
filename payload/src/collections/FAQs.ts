import type { CollectionConfig } from "payload";
import { FAQ_PAGE_OPTIONS } from "@shared/faq/pages";

import { authenticatedWrite, publishedOrAuthenticatedRead } from "../access";
import { defaultLexicalEditor } from "../lib/lexical";
import { SITE_ADMIN_GROUP } from "../lib/admin";

export const FAQs: CollectionConfig = {
  slug: "faqs",
  labels: {
    singular: "FAQ 页面",
    plural: "常见问题",
  },
  admin: {
    useAsTitle: "label",
    defaultColumns: ["label", "page", "createdAt"],
    group: SITE_ADMIN_GROUP,
    description: "各页面 FAQ（每页一条记录，条目在 items 中维护）。留空时官网回退代码默认内容。",
    listSearchableFields: ["label", "page"],
  },
  access: {
    read: publishedOrAuthenticatedRead,
    create: authenticatedWrite,
    update: authenticatedWrite,
    delete: authenticatedWrite,
  },
  versions: {
    drafts: true,
  },
  defaultSort: "createdAt",
  fields: [
    {
      name: "label",
      type: "text",
      required: true,
      admin: {
        description: "Admin 显示名，如「首页」「定价」",
      },
    },
    {
      name: "page",
      type: "select",
      required: true,
      unique: true,
      options: FAQ_PAGE_OPTIONS,
      admin: {
        description: "FAQ 所属页面（每页唯一）",
      },
    },
    {
      name: "items",
      type: "array",
      labels: { singular: "问题", plural: "FAQ 列表" },
      admin: {
        description: "拖拽调整顺序；留空时官网使用代码默认 FAQ",
        initCollapsed: false,
      },
      fields: [
        {
          name: "question",
          type: "text",
          required: true,
          admin: {
            description: "支持 {{siteName}} 占位符",
          },
        },
        {
          name: "label",
          type: "text",
          admin: {
            description: "平台/定价页左侧分类码（如「方法」「提示词」）；首页等可留空",
          },
        },
        {
          name: "answer",
          type: "richText",
          required: true,
          editor: defaultLexicalEditor,
          admin: {
            description: "FAQ 正文（富文本）；支持 {{siteName}} 占位符",
          },
        },
      ],
    },
  ],
};
