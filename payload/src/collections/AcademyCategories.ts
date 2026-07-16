import type { CollectionConfig } from "payload";

import { authenticatedWrite, publicRead } from "../access";
import { RESOURCE_EXPLORATION_ADMIN_GROUP } from "../lib/admin";

export const AcademyCategories: CollectionConfig = {
  slug: "academy-categories",
  labels: {
    singular: "学院分类",
    plural: "学院分类",
  },
  admin: {
    useAsTitle: "label",
    defaultColumns: ["label", "slug", "sortOrder", "updatedAt"],
    group: RESOURCE_EXPLORATION_ADMIN_GROUP,
    description: "学院列表「探索分类」胶囊。slug 用于 /academy/?category=",
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
          collection: "academies",
          where: { category: { equals: id } },
          limit: 1,
          depth: 0,
        });

        if (linked.totalDocs > 0) {
          throw new Error("该分类下仍有学院文章，请先修改或删除相关文章后再删除分类。");
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
        description: "小写英文或连字符，如 geo-guide；用于 /academy/?category=geo-guide",
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
