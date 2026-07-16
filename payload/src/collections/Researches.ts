import type { CollectionConfig } from "payload";

import { authenticatedWrite, publishedOrAuthenticatedRead } from "../access";
import { RESOURCE_EXPLORATION_ADMIN_GROUP } from "../lib/admin";
import { buildCollectionPreviewPath, buildPreviewUrl } from "../lib/preview";
import { contentLexicalEditor } from "../lib/lexical/content";

export const Researches: CollectionConfig = {
  slug: "researches",
  labels: {
    singular: "研究报告",
    plural: "研究报告",
  },
  admin: {
    useAsTitle: "cardTitle",
    defaultColumns: ["cardTitle", "slug", "category", "publishedAt", "updatedAt"],
    group: RESOURCE_EXPLORATION_ADMIN_GROUP,
    description: "研究列表卡片 + 详情正文 + SEO。Hero / 侧边 CTA / 目录由官网模板固定。",
    listSearchableFields: ["cardTitle", "slug", "cardDescription"],
    preview: (doc, { token }) => {
      const path = buildCollectionPreviewPath("researches", doc);
      return path ? buildPreviewUrl(path, token) : null;
    },
    components: {
      edit: {
        PreviewButton: "@/components/PreviewButton#PreviewButton",
      },
    },
  },
  access: {
    read: publishedOrAuthenticatedRead,
    create: authenticatedWrite,
    update: authenticatedWrite,
    delete: authenticatedWrite,
  },
  versions: {
    drafts: {
      autosave: {
        interval: 375,
      },
    },
  },
  defaultSort: "-publishedAt",
  fields: [
    {
      type: "tabs",
      tabs: [
        {
          label: "列表卡片",
          fields: [
            {
              name: "slug",
              type: "text",
              required: true,
              unique: true,
              index: true,
              label: "URL 标识",
              admin: {
                description: "路径：/research/{slug}/",
              },
            },
            {
              name: "cardTitle",
              type: "text",
              required: true,
              label: "卡片标题",
            },
            {
              name: "cardDescription",
              type: "textarea",
              required: true,
              label: "卡片摘要",
              admin: { description: "支持 {{siteName}} 占位符" },
            },
            {
              name: "cardLabels",
              type: "text",
              hasMany: true,
              label: "详情标签",
              admin: {
                description:
                  "详情页标题下方展示的标签（纯文案，非链接）。回车添加，类似品牌别名。",
              },
            },
            {
              name: "category",
              type: "relationship",
              relationTo: "research-categories",
              required: true,
              label: "分类",
            },
            {
              name: "cover",
              type: "upload",
              relationTo: "media",
              label: "卡片封面",
              admin: { description: "16:9 封面图；留空时官网回退默认封面" },
            },
            {
              name: "sortOrder",
              type: "number",
              defaultValue: 0,
              label: "排序权重",
              admin: { description: "越大越靠前；同权重按发布时间倒序" },
            },
            {
              name: "publishedAt",
              type: "date",
              label: "发布日期",
              admin: { date: { pickerAppearance: "dayOnly" } },
            },
          ],
        },
        {
          label: "详情正文",
          fields: [
            {
              name: "body",
              type: "richText",
              label: "正文",
              editor: contentLexicalEditor,
              admin: {
                description:
                  "H2 自动生成左侧目录。可用 Block：图片、高亮框、章节导语、行内 CTA；表格用编辑器内置表格。",
              },
            },
          ],
        },
      ],
    },
  ],
};
