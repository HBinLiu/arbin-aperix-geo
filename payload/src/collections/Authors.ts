import type { CollectionConfig } from "payload";
import { SOCIAL_PLATFORM_OPTIONS } from "@shared/social";

import { authenticatedWrite, publicRead } from "../access";
import { RESOURCE_EXPLORATION_ADMIN_GROUP } from "../lib/admin";
import { createBaiduPushAfterChangeHook } from "../lib/baiduPushHook";

export const Authors: CollectionConfig = {
  slug: "authors",
  labels: {
    singular: "编辑作者",
    plural: "编辑作者",
  },
  admin: {
    useAsTitle: "name",
    defaultColumns: ["name", "slug", "sortOrder", "updatedAt"],
    group: RESOURCE_EXPLORATION_ADMIN_GROUP,
    description: "博客编辑作者资料。官网路径：/authors/{slug}/",
    listSearchableFields: ["name", "slug"],
  },
  access: {
    read: publicRead,
    create: authenticatedWrite,
    update: authenticatedWrite,
    delete: authenticatedWrite,
  },
  defaultSort: "-sortOrder",
  hooks: {
    afterChange: [createBaiduPushAfterChangeHook("authors")],
    beforeDelete: [
      async ({ id, req }) => {
        const linkedBlog = await req.payload.find({
          collection: "blogs",
          where: { author: { equals: id } },
          limit: 1,
          depth: 0,
        });

        if (linkedBlog.totalDocs > 0) {
          throw new Error("该编辑作者仍有关联博客文章，请先修改或删除相关文章后再删除。");
        }
      },
    ],
  },
  fields: [
    {
      name: "slug",
      type: "text",
      required: true,
      unique: true,
      index: true,
      label: "URL 标识",
      admin: { description: "路径：/authors/{slug}/" },
    },
    {
      name: "name",
      type: "text",
      required: true,
      label: "姓名",
    },
    {
      name: "avatar",
      type: "upload",
      relationTo: "media",
      label: "头像",
    },
    {
      name: "bio",
      type: "textarea",
      required: true,
      label: "简介",
      admin: { description: "作者页 Hero 长文案；支持 {{siteName}}" },
    },
    {
      name: "socialLinks",
      type: "array",
      label: "社交链接",
      labels: { singular: "链接", plural: "社交链接" },
      fields: [
        {
          name: "platform",
          type: "select",
          required: true,
          label: "平台",
          options: [...SOCIAL_PLATFORM_OPTIONS],
        },
        {
          name: "url",
          type: "text",
          required: true,
          label: "URL",
        },
      ],
    },
    {
      name: "sortOrder",
      type: "number",
      defaultValue: 0,
      label: "排序权重",
      admin: { description: "越大越靠前" },
    },
  ],
};
