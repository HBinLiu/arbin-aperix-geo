import type { PageSeoDefault } from "./types";

export const SCENE_PAGE_SEO = {
  "product-launch": {
    label: "产品发布",
    path: "/scene/product-launch/",
    titleTopic: "AI 新品冷启动发布策略 - 上线首日即获 AI 引用",
    description:
      "确保新产品从发布首日就被 AI 发现和引用。发布前规划、发布日战术和发布后加速，实现即时 AI 可见性。",
    keywords: "产品发布,AI冷启动,新品GEO,AI引用,{{siteName}},艾佩睿思",
  },
  "narrative-shaping": {
    label: "叙事构建",
    path: "/scene/narrative-shaping/",
    titleTopic: "塑造您的品牌叙事 - 掌控 AI 如何推荐您",
    description:
      "主动影响 AI 平台如何呈现和推荐您的品牌。叙事影响力的三个层级：直接、放大和生态系统策略。",
    keywords: "品牌叙事,AI推荐,叙事构建,GEO策略,{{siteName}},艾佩睿思",
  },
  "content-strategy": {
    label: "内容策略",
    path: "/scene/content-strategy/",
    titleTopic: "面向 AI 内容策略 - 构建 AI 主动转述的品牌叙事",
    description:
      "跨 AI 平台构建一致的品牌叙事。开发包含问题支柱、解决方案方法论和证据内容的整合内容策略，以建立 AI 信任。",
    keywords: "AI内容策略,品牌叙事,GEO内容,内容支柱,{{siteName}},艾佩睿思",
  },
  "competitive-positioning": {
    label: "竞争定位",
    path: "/scene/competitive-positioning/",
    titleTopic: "抢占 AI 搜索市场份额 - 竞争定位与差异化分析",
    description:
      "了解您在 AI 推荐中与竞争对手的对比情况。识别差距，发现机会，并执行策略以在 AI 中主导您的品类。",
    keywords: "竞争定位,AI市场份额,差异化分析,GEO竞争,{{siteName}},艾佩睿思",
  },
  "brand-crisis-management": {
    label: "品牌危机管理",
    path: "/scene/brand-crisis-management/",
    titleTopic: "AI 品牌危机管理 - 实时声誉保护",
    description:
      "实时监控并响应负面 AI 提及。检测声誉风险，分析情感，并执行修正性内容策略以保护品牌信任。",
    keywords: "品牌危机,AI声誉,危机管理,情感监测,{{siteName}},艾佩睿思",
  },
} as const satisfies Record<string, PageSeoDefault>;
