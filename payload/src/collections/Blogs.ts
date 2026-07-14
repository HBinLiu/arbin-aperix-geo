import type { CollectionConfig } from "payload";

import { authenticatedWrite, publishedOrAuthenticatedRead } from "../access";
import { RESOURCE_EXPLORATION_ADMIN_GROUP } from "../lib/admin";
import { buildCollectionPreviewPath, buildPreviewUrl } from "../lib/preview";
import { blogLexicalEditor } from "../lib/lexical/blog";

export const Blogs: CollectionConfig = {
  slug: "blogs",
  labels: {
    singular: "博客文章",
    plural: "博客文章",
  },
  admin: {
    useAsTitle: "cardTitle",
    defaultColumns: ["cardTitle", "slug", "author", "publishedAt", "updatedAt"],
    group: RESOURCE_EXPLORATION_ADMIN_GROUP,
    description: "博客列表 + 详情正文 + SEO。侧栏「体验」CTA / 目录由官网模板固定。",
    listSearchableFields: ["cardTitle", "slug", "cardDescription"],
    preview: (doc, { token }) => {
      const path = buildCollectionPreviewPath("blogs", doc);
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
          label: "列表",
          fields: [
            {
              name: "slug",
              type: "text",
              required: true,
              unique: true,
              index: true,
              label: "URL 标识",
              admin: { description: "路径：/blog/{slug}/" },
            },
            {
              name: "cardTitle",
              type: "text",
              required: true,
              label: "标题",
            },
            {
              name: "cardDescription",
              type: "textarea",
              required: true,
              label: "摘要",
              admin: { description: "列表卡与详情 lead；支持 {{siteName}}" },
            },
            {
              name: "cover",
              type: "upload",
              relationTo: "media",
              label: "封面图",
            },
            {
              name: "category",
              type: "relationship",
              relationTo: "blog-categories",
              label: "分类",
              admin: { description: "探索分类筛选" },
            },
            {
              name: "author",
              type: "relationship",
              relationTo: "authors",
              required: true,
              label: "编辑作者",
            },
            {
              name: "readMinutes",
              type: "number",
              defaultValue: 5,
              min: 1,
              label: "阅读时长（分钟）",
            },
            {
              name: "publishedAt",
              type: "date",
              required: true,
              label: "发布日期",
              admin: {
                date: { pickerAppearance: "dayOnly" },
              },
            },
            {
              name: "sortOrder",
              type: "number",
              defaultValue: 0,
              label: "排序权重",
              admin: { description: "越大越靠前；同权重按发布时间倒序" },
            },
            {
              name: "isFeatured",
              type: "checkbox",
              defaultValue: false,
              label: "首页精选大图",
              admin: { description: "列表页左侧 Featured；多篇时取排序最前一篇" },
            },
            {
              name: "isEditorsPick",
              type: "checkbox",
              defaultValue: false,
              label: "编辑精选",
              admin: { description: "列表页右侧「编辑精选」栏" },
            },
            {
              name: "editorsPickOrder",
              type: "number",
              defaultValue: 0,
              label: "编辑精选排序",
              admin: {
                description: "越大越靠前；仅编辑精选生效",
                condition: (_, siblingData) => Boolean(siblingData?.isEditorsPick),
              },
            },
          ],
        },
        {
          label: "正文",
          fields: [
            {
              name: "body",
              type: "richText",
              label: "正文",
              editor: blogLexicalEditor,
            },
          ],
        },
      ],
    },
  ],
};
