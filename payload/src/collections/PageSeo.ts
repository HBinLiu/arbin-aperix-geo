import type { CollectionConfig } from "payload";
import { authenticatedWrite, publicRead, seedManagedCreate } from "../access";
import { SITE_ADMIN_GROUP } from "../lib/admin";

export const PageSeoEntries: CollectionConfig = {
  slug: "page-seo",
  labels: {
    singular: "页面",
    plural: "SEO设置",
  },
  admin: {
    useAsTitle: "label",
    defaultColumns: ["label", "path", "updatedAt"],
    group: SITE_ADMIN_GROUP,
    description: "各页面 title / description / keywords / OG 图。path 清单由代码默认 + seed 维护，不可在 Admin 新建。",
    listSearchableFields: ["label", "path"],
  },
  access: {
    read: publicRead,
    create: seedManagedCreate,
    update: authenticatedWrite,
    delete: authenticatedWrite,
  },
  defaultSort: "path",
  fields: [
    {
      name: "label",
      type: "text",
      required: true,
      admin: {
        description: "Admin 显示名称，如「首页」「定价」",
      },
    },
    {
      name: "path",
      type: "text",
      required: true,
      unique: true,
      admin: {
        description: "官网路径，根路径填 /；其余带尾斜杠，如 /pricing/",
      },
    },
    {
      name: "noindex",
      type: "checkbox",
      label: "禁止搜索引擎收录",
      defaultValue: false,
    },
  ],
};
