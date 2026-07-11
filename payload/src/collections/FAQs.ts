import type { CollectionConfig } from "payload";
import { authenticatedWrite, publicRead } from "../access";

export const FAQs: CollectionConfig = {
  slug: "faqs",
  labels: {
    singular: "FAQ",
    plural: "FAQ",
  },
  admin: {
    useAsTitle: "question",
    defaultColumns: ["question", "page", "sortOrder", "updatedAt"],
    group: "官网内容",
    description: "首页常见问题。留空时官网回退代码中的默认 FAQ。",
  },
  access: {
    read: publicRead,
    create: authenticatedWrite,
    update: authenticatedWrite,
    delete: authenticatedWrite,
  },
  defaultSort: "sortOrder",
  fields: [
    {
      name: "page",
      type: "select",
      required: true,
      defaultValue: "home",
      options: [{ label: "首页", value: "home" }],
      admin: {
        description: "FAQ 所属页面，后续可扩展定价页等",
      },
    },
    {
      name: "question",
      type: "text",
      required: true,
      admin: {
        description: "支持 {{name}} 占位符",
      },
    },
    {
      name: "answer",
      type: "textarea",
      required: true,
      admin: {
        description: "支持 {{name}} 占位符",
      },
    },
    {
      name: "sortOrder",
      type: "number",
      required: true,
      defaultValue: 0,
      admin: {
        description: "越小越靠前",
      },
    },
  ],
};
