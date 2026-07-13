import type { CollectionConfig } from "payload";

import { authenticatedWrite, publicRead } from "../access";
import { RESOURCE_EXPLORATION_ADMIN_GROUP } from "../lib/admin";

export const ResearchCategories: CollectionConfig = {
  slug: "research-categories",
  labels: {
    singular: "研究分类",
    plural: "研究分类",
  },
  admin: {
    useAsTitle: "label",
    defaultColumns: ["label", "slug", "sortOrder", "updatedAt"],
    group: RESOURCE_EXPLORATION_ADMIN_GROUP,
    description: "研究报告列表筛选项。slug 用于官网 URL（?category=industry），请先建分类再创建报告。",
    listSearchableFields: ["label", "slug"],
  },
  access: {
    read: publicRead,
    create: authenticatedWrite,
    update: authenticatedWrite,
    delete: authenticatedWrite,
  },
  defaultSort: "-sortOrder",
  hooks: {
    beforeDelete: [
      async ({ id, req }) => {
        const linked = await req.payload.find({
          collection: "researches",
          where: { category: { equals: id } },
          limit: 1,
          depth: 0,
        });

        if (linked.totalDocs > 0) {
          throw new Error("该分类下仍有研究报告，请先修改或删除相关报告后再删除分类。");
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
      label: "标识",
      admin: {
        description: "小写英文或连字符，如 industry；用于官网 /research/?category=industry",
      },
    },
    {
      name: "label",
      type: "text",
      required: true,
      label: "展示名称",
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
