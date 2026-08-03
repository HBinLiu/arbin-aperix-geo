import type { GlobalConfig } from "payload";
import { authenticatedWrite, publicRead } from "../access";
import { SITE_ADMIN_GROUP } from "../lib/admin";

export const AboutPage: GlobalConfig = {
  slug: "about-page",
  label: "关于我们",
  admin: {
    group: SITE_ADMIN_GROUP,
    description: "管理 /about 的「我们的故事」。",
  },
  access: {
    // Global 不支持 Collection 式 Where；公开读由草稿机制只返回已发布版本。
    read: publicRead,
    update: authenticatedWrite,
  },
  versions: {
    drafts: {
      autosave: {
        interval: 375,
      },
    },
  },
  fields: [
    {
      type: "tabs",
      tabs: [
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
                  name: "content",
                  type: "richText",
                  label: "正文",
                  required: true,
                  admin: {
                    description: "富文本正文；文本中可使用 {{siteName}} 占位符",
                  },
                },
              ],
            },
          ],
        },
      ],
    },
  ],
};
