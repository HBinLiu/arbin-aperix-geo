import type { CollectionConfig } from "payload";

import { authenticatedWrite, publishedOrAuthenticatedRead } from "../access";
import { RESOURCE_EXPLORATION_ADMIN_GROUP, adminDayOnlyDate } from "../lib/admin";
import { createBaiduPushAfterChangeHook } from "../push/baidu";
import { createIndexNowPushAfterChangeHook } from "../push/indexnow";
import { buildCollectionPreviewPath, buildPreviewUrl } from "../lib/preview";
import { contentLexicalEditor } from "../lib/lexical/content";

export const News: CollectionConfig = {
  slug: "news",
  labels: {
    singular: "产品新闻",
    plural: "产品新闻",
  },
  admin: {
    useAsTitle: "cardTitle",
    defaultColumns: ["cardTitle", "slug", "publishedAt", "updatedAt"],
    group: RESOURCE_EXPLORATION_ADMIN_GROUP,
    description: "产品新闻列表 + 详情正文 + SEO。侧边 CTA / 目录由官网模板固定。",
    listSearchableFields: ["cardTitle", "slug", "cardDescription"],
    preview: (doc, { token }) => {
      const path = buildCollectionPreviewPath("news", doc);
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
  hooks: {
    afterChange: [
      createBaiduPushAfterChangeHook("news"),
      createIndexNowPushAfterChangeHook("news"),
    ],
  },
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
              admin: {
                description: "路径：/news/{slug}/",
              },
            },
            {
              name: "cardTitle",
              type: "text",
              required: true,
              label: "列表标题",
            },
            {
              name: "cardDescription",
              type: "textarea",
              required: true,
              label: "摘要",
              admin: { description: "详情页 lead 默认回退；支持 {{siteName}} 占位符" },
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
              required: true,
              label: "发布日期",
              admin: {
                description: "列表按月分组依据",
                date: adminDayOnlyDate,
              },
            },
          ],
        },
        {
          label: "详情 Hero",
          fields: [
            {
              name: "tag",
              type: "text",
              label: "角标",
              admin: { description: "如「GEO 新闻简报 · AI 可见性」" },
            },
            {
              name: "sourceAuthor",
              type: "text",
              label: "原文作者",
            },
            {
              name: "sourceUrl",
              type: "text",
              label: "原文链接",
            },
            {
              name: "sourceLabel",
              type: "text",
              label: "原文来源名",
              admin: { description: "链接展示文案，留空则从 URL 推断" },
            },
            {
              name: "readMinutes",
              type: "number",
              min: 1,
              defaultValue: 5,
              label: "阅读时间（分钟）",
            },
            {
              name: "editorNote",
              type: "textarea",
              label: "编辑说明",
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
                  "H2 与「简要列表」「双栏信息卡」自动生成目录。Block：简要列表、引用框、插入图片、高亮框、章节导语、双栏信息卡、行内 CTA；表格用内置表格。",
              },
            },
          ],
        },
      ],
    },
  ],
};
