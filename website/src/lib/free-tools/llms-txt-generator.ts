import { llmsTxtGeneratorFaqDefaults } from "@shared/faq/defaults";
import type { Faq, FaqDoc } from "@/lib/faqs";
import { mergeFaqs, resolveFaqDefaults } from "@/lib/faqs";
import { appLinks } from "@/lib/app-links";
import { resolveSiteCopyDeep } from "@/lib/site";

export const llmsTxtPreviewPlaceholder = `# llms.txt

输入可访问的网站 URL，生成真实的 llms.txt 文件

提交后我们会读取你的网站 sitemap，提取关键页面，并把真实生成结果返回到这里。`;

export const llmsTxtGeneratorContent = resolveSiteCopyDeep({
  eyebrow: "免费工具",
  title: "让 AI 更准确地理解、引用和推荐你的网站",
  description:
    "输入网址，生成一份适合豆包、DeepSeek、通义千问、腾讯元宝、Kimi 和文心一言等 AI 工具读取的 LLMs.txt 草稿。适合 SaaS、出海品牌、内容站、工具站，用于整理品牌介绍、核心页面、产品能力和 AI 可引用信息。",
  form: {
    urlLabel: "网站 URL",
    urlPlaceholder: "https://example.com",
    submitLabel: "免费生成 LLMs.txt",
    note: "提交可访问的网站 URL 后，会返回真实生成结果。",
    previewTitle: "LLMs.txt 预览",
    previewPath: "/llms.txt",
    previewFootnote: "当前仅为预览，不会从本页真正发布文件。",
    chips: ["免费使用", "无需写代码", "发布前先预览"],
  },
  sidebar: {
    title: "生成文件，只是第一步。",
    description:
      "一份清晰的 LLMs.txt 草稿可以把 AI 引到更正确的方向，但它并不能保证你的关键页面真的容易被发现、被理解、被引用。\n我们还可以检查你的品牌在豆包、DeepSeek、通义千问、腾讯元宝、Kimi 和文心一言等 AI 平台中的可见度、误读风险和竞品差距。",
    ctaLabel: "注册体验全站审计",
    ctaHref: appLinks.register,
    relatedTools: {
      title: "相关工具",
      items: [
        {
          title: "单页审计",
          description: "检查你的关键页面是否能被 AI 抓取器访问、读取，并被大语言模型解析。",
          href: "/free-tools/single-page-audit/",
        },
      ],
    },
  },
  howItWorks: {
    title: "如何工作",
    intro: "这个页面的目标，是让你先看到一份可用的 LLMs.txt 草稿，再决定如何发布和维护。",
    steps: [
      {
        label: "Step 1",
        title: "输入你要描述的网站",
        description: "使用首页 URL 或你想让 AI 理解的主域名。",
      },
      {
        label: "Step 2",
        title: "查看 LLMs.txt 输出",
        description: "预览展示的是一类常见的精简结构，通常会发布在 /llms.txt。",
      },
      {
        label: "Step 3",
        title: "发布前按页面建议整理内容",
        description: "确认草稿方向正确后，再回头检查关键页面、发布文件，并在站点变化时维护它。",
      },
    ],
  },
  whatIsLlms: {
    title: "什么是 llms.txt",
    cards: [
      "LLMs.txt 是一个轻量文本文件，帮助 AI 用更直接的方式理解你的网站。它通常会列出你希望模型优先阅读的页面，并补充简短说明，解释这些页面为什么重要。",
      "它并非现有技术文件的正式替代品，而是一个面向 AI 的内容导览。它可以帮助答案引擎和 AI 系统更快找到并理解最能代表您品牌、产品和文档的关键页面。",
    ],
  },
  whyItMatters: {
    title: "为什么它重要",
    intro:
      "越来越多用户正在通过豆包、DeepSeek、通义千问、腾讯元宝、Kimi 和文心一言等 AI 工具发现产品、比较方案、寻找服务商。\n如果你的网站没有清晰地告诉 AI「你是谁、做什么、适合谁、哪些页面最重要」，AI 就可能忽略你、误读你，或者引用到不准确的内容。\nLLMs.txt 的作用，是把你希望 AI 优先理解的信息整理成一份清晰的入口文件：",
    items: [
      "帮助 AI 更快理解你的品牌、产品、服务和目标客户",
      "引导 AI 找到最重要的页面，比如首页、产品页、文档、案例和价格页",
      "减少 AI 对你业务的误读、遗漏和错误总结",
      "为 GEO / AI 生成式引擎优化提供基础结构",
      "让你的网站更适合被 AI 工具读取、引用和推荐",
    ],
    closing:
      "它不会保证你立刻出现在 AI 回答里，但它能让你的网站从「等 AI 自己猜」变成「主动告诉 AI 该如何理解你」。",
  },
  fileComparison: {
    title: "LLMs.txt、robots.txt 与 sitemap.xml 的区别",
    intro: "这些文件解决的是不同问题。它们更适合互相补充，而不是互相替代。",
    columns: ["维度", "LLMs.txt", "robots.txt", "sitemap.xml"],
    rows: [
      {
        item: "主要用途",
        llms: "说明哪些页面重要，以及应该怎样理解它们",
        robots: "控制抓取访问规则",
        sitemap: "列出待发现的 URL",
      },
      {
        item: "最适合表达",
        llms: "品牌、产品、文档与重点上下文",
        robots: "允许或阻止路径",
        sitemap: "帮助引擎发现页面",
      },
      {
        item: "典型内容",
        llms: "简短摘要和分组链接",
        robots: "规则与指令",
        sitemap: "结构化 URL 清单",
      },
    ],
  },
  howToPublish: {
    title: "如何发布它",
    intro: "真正执行起来并不复杂，关键在于页面选择是否准确，以及后续是否持续维护。",
    steps: [
      {
        label: "Step 1",
        title: "先写一句简短的网站摘要",
        description: "用一两句话说明公司做什么，以及 AI 应该把哪些页面当作主要来源。",
      },
      {
        label: "Step 2",
        title: "只列最重要的页面",
        description: "优先包含产品、价格、文档、帮助和教育内容，而不是把所有 URL 都放进去。",
      },
      {
        label: "Step 3",
        title: "发布到站点根目录",
        description: "推荐发布在 /.well-known/llms.txt 或根目录 /llms.txt 下，这样路径更规范也更稳定。",
      },
      {
        label: "Step 4",
        title: "当优先级变化时及时更新",
        description: "新产品上线、旧页面替换、文档结构调整后，都应该重新整理这份文件。",
      },
    ],
  },
  audience: {
    title: "适合谁使用",
    items: [
      "想先做一次低门槛整理，再决定是否继续做 AI visibility 深度工作的站点负责人",
      "需要先定义「哪些 URL 代表品牌」的 SEO、GEO 和内容团队",
      "文档较多的产品团队，希望更快把模型引导到产品页、上手文档和支持内容",
    ],
  },
  relatedTools: {
    eyebrow: "免费工具",
    title: "继续探索其他免费工具",
    description:
      "从文件生成、页面审计到提示词和信源分析，快速看清 AI 系统如何读取、引用和比较你的品牌。",
  },
});

export type LlmsTxtRelatedTool = {
  title: string;
  description: string;
  href: string;
  current?: boolean;
};

export const llmsTxtRelatedTools: LlmsTxtRelatedTool[] = [
  {
    title: "单页审计",
    description: "快速审计页面是否适合被 AI 理解和引用。",
    href: "/free-tools/single-page-audit/",
  },
  {
    title: "热门提示词发现器",
    description: "发现用户在 AI 引擎中搜索的热门提示词。",
    href: "/free-tools/hot-prompt-finder/",
  },
];

export const llmsTxtGeneratorFaqs: Faq[] = resolveFaqDefaults(llmsTxtGeneratorFaqDefaults);

export function mergeLlmsTxtGeneratorFaqs(cms: FaqDoc[] | null | undefined): Faq[] {
  return mergeFaqs(cms, llmsTxtGeneratorFaqs);
}
