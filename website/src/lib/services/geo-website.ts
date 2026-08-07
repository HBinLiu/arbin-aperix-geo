import type { CtaContent } from "@/lib/home";
import { mergeFaqs, resolveFaqDefaults, type Faq, type FaqDoc } from "@/lib/faqs";
import { resolveSiteCopyDeep } from "@/lib/site";
import { appLinks } from "@/lib/app-links";
import { geoWebsiteFaqDefaults } from "@shared/faq/defaults";

export type EraColumn = {
  era: string;
  role: string;
  audience: string;
  success: string;
};

export type ServicePoint = {
  title: string;
  description: string;
};

export const geoWebsitePage = resolveSiteCopyDeep({
  hero: {
    title: "GEO 时代，官网仍是品牌重要的可引用源",
    descriptionLines: [
      "搜索从「排名列表」变成「模型回答」。官网要同时被人读懂、被模型信任。",
      "我们提供面向 GEO 的官网定制与改造服务。",
    ],
    primaryCtaLabel: "咨询官网定制",
    primaryCtaHref: "/contact/",
    secondaryCtaLabel: "了解监测产品",
    secondaryCtaHref: "/",
  },
  eras: {
    title: "官网角色变了，不是不重要了",
    columns: [
      {
        era: "门户时代",
        role: "品牌门面与信息发布",
        audience: "人浏览、人点击",
        success: "访问量、停留、留资",
      },
      {
        era: "SEO 时代",
        role: "关键词落地与转化漏斗",
        audience: "搜索引擎抓取 + 人点击",
        success: "排名、自然流量、转化",
      },
      {
        era: "GEO 时代",
        role: "权威来源与可引用资产",
        audience: "人 + AI 模型共同消费",
        success: "被引用、被推荐、被信任",
      },
    ] satisfies EraColumn[],
  },
  why: {
    title: "为什么 GEO 时代更需要认真做官网",
    descriptionLines: [
      "模型不会「逛」你的品牌故事，它只会抽取可验证、可引用的事实。",
      "官网是你能控制的少数权威源之一。",
    ],
    points: [
      {
        title: "回答引擎优先引用权威站",
        description:
          "豆包、DeepSeek、通义等生成答案时，倾向采信结构清晰、信息完整、可核验的官方页面。",
      },
      {
        title: "SEO 流量不等于 AI 可见",
        description:
          "排在搜索结果前列，不代表会出现在模型回答里。GEO 要求内容可解析、可摘要、可对齐实体。",
      },
      {
        title: "官网是品牌知识库的底座",
        description:
          "产品定义、定位、案例、FAQ、政策条款——这些结构化内容决定模型「如何介绍你」。",
      },
      {
        title: "与监测闭环联动",
        description:
          "定制官网解决「被引用的材料」；{{siteName}} 监测解决「有没有被提到」。两者一起，才形成 GEO 增长闭环。",
      },
    ] satisfies ServicePoint[],
  },
  offer: {
    title: "我们提供什么",
    description: "不是套模板上线，而是按 GEO 目标重建官网的信息架构与表达方式。",
    items: [
      {
        title: "信息架构与内容模型",
        description: "栏目、实体页、FAQ、案例与证据链，让人与模型都能快速定位关键事实。",
      },
      {
        title: "SEO 与 GEO 基础共建",
        description: "技术 SEO、sitemap / robots / llms.txt、结构化数据与可抓取性能一并落地。",
      },
      {
        title: "品牌叙事与可引用表达",
        description: "把口号写成可核验陈述：做什么、服务谁、凭什么、如何证明。",
      },
      {
        title: "改造或全新定制",
        description: "支持现有站 GEO 改造，或全新官网定制，对接你的转化与运营流程。",
      },
    ] satisfies ServicePoint[],
  },
});

export const geoWebsiteCta: CtaContent = resolveSiteCopyDeep({
  badge: "定制服务",
  titleBefore: "准备好建设",
  titleHighlight: "可被 AI 引用",
  titleAfter: "的官网了吗？",
  description:
    "告诉我们你的品牌与目标站点，{{siteName}} 团队将评估改造或全新定制方案。",
  codeLines: ["// 给人看。", "// 也给模型读。"],
  secondaryCtaLabel: "预约沟通",
  secondaryCtaHref: "/contact/",
  primaryCtaLabel: "注册试用",
  primaryCtaHref: appLinks.register,
});

export const geoWebsiteFaqs: Faq[] = resolveFaqDefaults(geoWebsiteFaqDefaults);

export function mergeGeoWebsiteFaqs(cms: FaqDoc[] | null | undefined): Faq[] {
  return mergeFaqs(cms, geoWebsiteFaqs);
}
