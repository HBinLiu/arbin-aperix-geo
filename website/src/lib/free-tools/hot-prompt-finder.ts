import { hotPromptFinderFaqDefaults } from "@shared/faq/defaults";
import type { Faq, FaqDoc } from "@/lib/faqs";
import { mergeFaqs, resolveFaqDefaults } from "@/lib/faqs";
import { appLinks } from "@/lib/app-links";
import { resolveSiteCopyDeep } from "@/lib/site";

export const hotPromptPreviewPlaceholder = `发现你的目标客户正在问 AI 的高价值问题

输入品牌域名和核心业务线，识别与你业务相关的 AI 搜索问题、购买意图和内容机会，帮助你判断哪些提示词值得持续监测和优化。`;

export const hotPromptFinderContent = resolveSiteCopyDeep({
  eyebrow: "免费工具",
  title: "发现你的目标客户正在问 AI 的高价值问题",
  description:
    "输入品牌域名和核心业务线，识别与你业务相关的 AI 搜索问题、购买意图和内容机会，帮助你判断哪些提示词值得持续监测和优化。",
  form: {
    domainLabel: "官网域名或链接",
    domainPlaceholder: "example.com",
    businessLineLabel: "核心业务线",
    businessLinePlaceholder: "例如：AI 内容营销、企业 SaaS、在线教育",
    submitLabel: "查找高价值提示词",
    previewTitle: "高价值提示词分析结果",
    previewPath: "/report.html",
    previewFootnote:
      "我们会结合网站内容、目标市场、行业关键词和 AI 搜索意图，识别与你业务最相关的 AI 搜索问题机会。",
  },
  sidebar: {
    title: "这些问题下，AI 现在推荐谁？",
    description:
      "{{siteName}} 可以继续帮你追踪这些提示词在豆包、DeepSeek、通义千问、腾讯元宝、Kimi 和文心一言等平台中的回答表现，分析品牌可见度、竞品占位、引用来源和内容缺口。",
    ctaLabel: "监测我的 AI 搜索提示词",
    ctaHref: appLinks.register,
    relatedTools: {
      title: "相关工具",
      items: [
        {
          title: "单页审计",
          description: "检查你的关键页面是否能被 AI 抓取器访问、读取，并被大语言模型解析。",
          href: "/free-tools/single-page-audit/",
        },
        {
          title: "LLMs.txt 生成器",
          description: "生成一份 AI 可读网站指南文件，帮助 AI 爬虫识别和理解你的关键页面。",
          href: "/free-tools/llms-txt-generator/",
        },
      ],
    },
  },
  howItFinds: {
    title: "它是怎么找到这些问题的？",
    intro:
      "这个工具会先读取你的品牌域名和核心业务线，理解你提供什么、服务谁、属于哪个市场，并推断目标客户在 AI 工具中可能提出的高意图问题。",
    highlight:
      "它不是随机生成 AI 搜索提示词，而是从<strong>业务相关性、搜索意图、购买阶段和内容机会</strong>四个维度筛选出值得持续监测的问题。",
  },
  whatPromptsMean: {
    title: "这些 AI 搜索提示词 代表什么？",
    intro: "这些 AI 搜索提示词 不是普通 SEO 关键词，而是用户在 AI 问答引擎里表达需求的方式。",
    subtitle: "它们通常代表三类机会：",
    opportunities: [
      {
        tone: "need",
        title: "需求机会",
        description: "用户正在寻找某类解决方案",
        example: '"best tools for AI search visibility"',
      },
      {
        tone: "compare",
        title: "比较机会",
        description: "用户正在比较品牌、替代品或方案",
        example: '"alternative to [competitor] for AI search monitoring"',
      },
      {
        tone: "problem",
        title: "问题机会",
        description: "用户遇到痛点，希望 AI 推荐解决方案或产品",
        example: '"what tool can help improve website traffic?"',
      },
    ],
    closing: "如果你的品牌没有出现在这些问题的 AI 回答里，用户可能会直接看到竞品。",
  },
  whyItMatters: {
    title: "为什么高价值提示词很重要？",
    intro:
      "在 AI 搜索里，用户不是只输入一个关键词，而是直接提出完整问题。这些问题往往暴露了更明确的需求、场景和购买意图。",
    lead: "对品牌来说，真正值得关注的不是所有提示词，而是那些会影响发现、比较和购买决策的问题：",
    items: [
      "用户在找解决方案时，AI 是否会提到你",
      "用户比较供应商时，你是否被纳入候选名单",
      "用户询问竞品替代方案时，你是否出现",
      "用户描述痛点时，AI 是否能把你的产品和问题匹配起来",
    ],
    closing: "持续监测这些提示词，可以帮助你发现 AI 搜索中的曝光缺口、竞品机会和内容优先级。",
  },
  howToUse: {
    title: "如何使用这些结果？",
    intro: "你可以把这些提示词当作 AI 搜索优化的任务清单，而不只是内容灵感。建议这样使用：",
    items: [
      '优先开始监测漏斗底部提示词：比如 "best tools"、"alternatives"、"vs"、"pricing"、"for enterprise" 等问题，它们更接近购买决策。',
      "检查 AI 回答里是否出现你的品牌：如果竞品出现而你没有出现，这就是明确的 AI 可见度差距。",
      "为高机会提示词创建或优化页面：包括对比页、替代方案页、场景页、行业页、FAQ 和案例页。",
      "持续监测这些提示词下的 AI 回答变化：AI 回答会随着内容、引用源和模型变化而变化，重要提示词应该定期复查。",
    ],
  },
  audience: {
    title: "适合谁使用？",
    items: [
      "B2B SaaS、开发者工具、API 平台和数据服务",
      "出海品牌和正在进入新市场的团队",
      "SEO、内容营销和增长团队",
      "正在做 GEO / AI 搜索优化 的品牌",
      "想知道竞品在哪些 AI 问题里被推荐的团队",
    ],
  },
  relatedTools: {
    eyebrow: "免费工具",
    title: "继续探索其他免费工具",
    description:
      "从文件生成、页面审计到提示词和信源分析，快速看清 AI 系统如何读取、引用和比较你的品牌。",
  },
});

export type HotPromptRelatedTool = {
  title: string;
  description: string;
  href: string;
  current?: boolean;
};

export const hotPromptRelatedTools: HotPromptRelatedTool[] = [
  {
    title: "单页审计",
    description: "快速审计页面是否适合被 AI 理解和引用。",
    href: "/free-tools/single-page-audit/",
  },
  {
    title: "LLMs.txt 生成器",
    description: "生成一份 AI 可读网站指南文件，帮助 AI 爬虫识别和理解你的关键页面。",
    href: "/free-tools/llms-txt-generator/",
  },
];

export const hotPromptFinderFaqs: Faq[] = resolveFaqDefaults(hotPromptFinderFaqDefaults);

export function mergeHotPromptFinderFaqs(cms: FaqDoc[] | null | undefined): Faq[] {
  return mergeFaqs(cms, hotPromptFinderFaqs);
}
