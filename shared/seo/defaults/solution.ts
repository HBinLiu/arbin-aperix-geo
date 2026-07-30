import type { PageSeoDefault } from "./types";

export const SOLUTION_TEAM_SEO = {
  agencies: {
    label: "代理商",
    path: "/solution/agencies/",
    titleTopic: "面向代理商：规模化多品牌 AI 管理解决方案",
    description:
      "在一个平台管理所有客户的 AI 可见性。白标仪表盘、批量报告和团队权限。无需招聘新专家即可扩展 GEO 业务。",
  },
  enterprise: {
    label: "大型企业",
    path: "/solution/enterprise/",
    titleTopic: "面向大型企业团队：AI 品牌影响力与信任建设策略",
    description:
      "面向大型组织的战略平台，旨在提升 AI 品牌影响力和信任度。高管仪表盘、定制集成和专属支持，助力品牌主导地位。",
  },
  "pr-brand-teams": {
    label: "公关与品牌团队",
    path: "/solution/pr-brand-teams/",
    titleTopic: "面向公关与品牌团队：塑造 AI 对话中的品牌形象",
    description:
      "跨 AI 平台监控品牌声誉。追踪情感、竞争定位并塑造叙事。实时危机检测和声誉管理。",
  },
  "smb-geo-teams": {
    label: "中小企业 GEO 团队",
    path: "/solution/smb-geo-teams/",
    titleTopic: "面向中小企业团队：提升 AI 可见性并构建品牌信任",
    description:
      "面向小团队的简单、实惠的 GEO 平台。快速 AI 就绪诊断、一键监控和可落地建议。无需 GEO 专家。",
  },
  "seo-specialists": {
    label: "SEO 专家",
    path: "/solution/seo-specialists/",
    titleTopic: "面向 SEO 从业者 - 高性价比且专业的 GEO 优化工具",
    description:
      "专为独立 SEO 顾问打造的实惠 GEO 平台。AI 可见性追踪、竞争分析和报告工具。以低成本最大化客户价值。",
  },
} as const satisfies Record<string, PageSeoDefault>;
