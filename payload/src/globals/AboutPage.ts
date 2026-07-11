import type { GlobalConfig } from "payload";
import { authenticatedWrite, publishedOrAuthenticatedGlobalRead } from "../access";

export const AboutPage: GlobalConfig = {
  slug: "about-page",
  label: "关于页",
  admin: {
    group: "官网内容",
    description: "管理 /about 的「我们的故事」与 SEO。Hero、价值观等仍由代码维护。",
  },
  access: {
    read: publishedOrAuthenticatedGlobalRead,
    update: authenticatedWrite,
  },
  versions: {
    drafts: true,
  },
  fields: [
    {
      type: "tabs",
      tabs: [
        {
          label: "SEO",
          fields: [
            {
              name: "seo",
              type: "group",
              fields: [
                {
                  name: "title",
                  type: "text",
                  label: "页面标题",
                  admin: {
                    description: "留空则使用代码中的默认 SEO；支持 {{name}}",
                  },
                },
                {
                  name: "description",
                  type: "textarea",
                  label: "页面描述",
                  admin: {
                    description: "支持 {{name}}",
                  },
                },
              ],
            },
          ],
        },
        {
          label: "我们的故事",
          fields: [
            {
              name: "story",
              type: "group",
              fields: [
                {
                  name: "title",
                  type: "text",
                  label: "区块标题",
                  defaultValue: "我们的故事",
                },
                {
                  name: "paragraphs",
                  type: "array",
                  label: "段落",
                  admin: {
                    description: "支持 {{name}} 占位符，将替换为品牌名",
                  },
                  fields: [
                    {
                      name: "text",
                      type: "textarea",
                      label: "段落内容",
                      required: true,
                    },
                  ],
                },
              ],
            },
          ],
        },
      ],
    },
  ],
};
