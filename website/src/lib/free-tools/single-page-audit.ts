import { singlePageAuditFaqDefaults } from "@shared/faq/defaults";
import type { Faq, FaqDoc } from "@/lib/faqs";
import { mergeFaqs, resolveFaqDefaults } from "@/lib/faqs";
import { appLinks } from "@/lib/app-links";
import { resolveSiteCopyDeep } from "@/lib/site";

export const singlePageAuditPreviewPlaceholder = `<!doctype html>
<html>
  <body>
    <h1>结果将在这里显示</h1>
    <p>输入一个可访问的页面 URL，生成当前页面的 HTML 审计报告预览。</p>
  </body>
</html>`;

export const singlePageAuditContent = resolveSiteCopyDeep({
  eyebrow: "免费审计工具",
  title: "几秒钟检查你的页面是否适合被 AI 理解和引用",
  description:
    "输入任意页面 URL，快速发现标题、结构、内容清晰度和 AI 可读性问题，判断这个页面是否已经准备好出现在豆包、DeepSeek、通义千问、腾讯元宝、Kimi 和文心一言等 AI 回答中。",
  form: {
    urlLabel: "页面 URL",
    urlPlaceholder: "https://example.com",
    submitLabel: "免费审计页面",
    note: "提交后会创建真实任务，并在完成后返回可下载的 HTML 审计报告。",
    previewTitle: "审计预览",
    previewPath: "/audit.html",
    previewFootnote: "报告基于当前 URL 的单页快照生成，不等于整站审计。",
    chips: ["可免费试用", "检查页面清晰度与抓取准备度", "几秒内预览关键问题"],
  },
  sidebar: {
    title: "快速审计，只是起点。",
    description:
      "单个页面只是入口，真正的问题是：AI 是否能理解你的整个品牌。\n我们可以继续检查你的品牌在豆包、DeepSeek、通义千问、腾讯元宝、Kimi 和文心一言等 AI 平台中的可见度、误读风险、竞品差距和内容机会。",
    ctaLabel: "注册体验全站审计",
    ctaHref: appLinks.register,
    relatedTools: {
      title: "相关工具",
      items: [
        {
          title: "LLMs.txt 生成器",
          description: "生成一份 AI 可读网站指南文件，帮助 AI 爬虫识别和理解你的关键页面。",
          href: "/free-tools/llms-txt-generator/",
        },
      ],
    },
  },
  howItWorks: {
    title: "工作方式",
    intro: "这个页面的目标，是让首轮结果足够快地产生价值，而不是先把你带进一个复杂仪表盘。",
    steps: [
      {
        label: "Step 1",
        title: "输入你要检查的页面",
        description: "可以是落地页、价格页、功能页、博客文章，或文档入口页。",
      },
      {
        label: "Step 2",
        title: "先看首轮结果摘要",
        description: "这个 mock 结果会优先展示得分、最重要的问题，以及最快可以做的改进。",
      },
      {
        label: "Step 3",
        title: "判断是否需要更深层的审计",
        description: "如果快速审计已经暴露出清晰度、结构或信任信号问题，就可以继续进入更完整的工作流。",
      },
    ],
  },
  auditScope: {
    title: "这个审计会看什么",
    intro:
      "我们会从 AI 读取网页的角度，检查这个页面是否清楚表达了「你是谁、提供什么、适合谁、为什么值得被推荐」",
    items: [
      "页面标题和 H1 是否清楚表达核心价值",
      "首屏是否说明产品、服务或页面主题",
      "内容结构是否容易被 AI 拆解和总结",
      "是否包含目标用户、使用场景、优势和证据",
      "重要信息是否被隐藏在图片、动画或难以读取的组件中",
      "title、description、canonical、schema 等基础信号是否完整",
    ],
  },
  understandResults: {
    title: "如何理解这个结果",
    intro:
      "这个分数不是传统 SEO 排名预测，也不是流量评分。它衡量的是：当 AI 模型读取这个页面时，是否能快速、准确地理解页面主题、品牌定位、核心价值和下一步应该引用的内容。",
    items: [
      "高分页面通常有清晰的标题、明确的首屏说明、结构化内容、可信证据和可被引用的文字信息。",
      "低分页面往往不是内容少，而是关键信息分散、表达模糊，或者 AI 无法判断这个页面最重要的结论是什么。",
    ],
  },
  previewHighlights: {
    title: "本次审计预览的重点内容",
    intro: "一个快速审计之所以有用，是因为它能把检查项和真实页面结果直接关联起来。",
    columns: ["检查项", "为什么重要", "可能发现什么问题"],
    rows: [
      {
        item: "页面框架",
        why: "第一屏应该尽量不依赖额外解释，就能让人知道页面是关于什么的。",
        issues: "hero 文案泛化、标题偏弱、价值表达出现过晚",
      },
      {
        item: "区块层级",
        why: "清晰层级能帮助用户和模型更快识别「什么最重要」。",
        issues: "区块互相竞争、标题不清楚、扫描路径偏弱",
      },
      {
        item: "信任与证明",
        why: "当关键结论附近就能看到证据，页面更容易转化，也更容易建立可信度。",
        issues: "缺少案例、评价、数字结果或来源提示",
      },
      {
        item: "结构信号",
        why: "元信息和标题结构会影响页面如何被理解、整理和呈现。",
        issues: "title 偏松、description 缺失、标题层级过浅",
      },
    ],
  },
  commonIssues: {
    title: "这个工具发现的常见问题",
    intro: "很多表现不佳的页面并不是技术上坏掉了，而是没有按正确顺序表达正确的信息。",
    items: [
      "标题太泛，无法直接说明页面提供什么。",
      "开头内容太长，导致关键信息出现得太晚。",
      "首屏附近缺少证明点、案例或信任信号。",
      "多个区块结构和视觉权重相近，难以区分主次。",
      "元信息或标题层级没有真正强化页面核心意图。",
    ],
  },
  goodPages: {
    title: "什么样的页面更容易被 AI 和用户理解",
    intro: "通常最强的页面，也正是最容易被阅读、被总结、被采取的页面。",
    items: [
      "第一屏就有清楚的页面承诺。",
      "每个区块都有具体且有解释力的标题。",
      "关键结论附近有可信佐证，例如案例、评价、数据、来源等。",
      "概览、细节、证明和行动之间有清楚分工。",
    ],
  },
  relatedTools: {
    eyebrow: "免费工具",
    title: "继续探索其他免费工具",
    description:
      "从文件生成、页面审计到提示词和信源分析，快速看清 AI 系统如何读取、引用和比较你的品牌。",
  },
});

export type SinglePageAuditRelatedTool = {
  title: string;
  description: string;
  href: string;
  current?: boolean;
};

export const singlePageAuditRelatedTools: SinglePageAuditRelatedTool[] = [
  {
    title: "LLMs.txt 生成器",
    description: "生成一份 AI 可读网站指南文件，帮助 AI 爬虫识别和理解你的关键页面。",
    href: "/free-tools/llms-txt-generator/",
  },
  {
    title: "热门提示词发现器",
    description: "发现用户在 AI 引擎中搜索的热门提示词。",
    href: "/free-tools/hot-prompt-finder/",
  },
];

export const singlePageAuditFaqs: Faq[] = resolveFaqDefaults(singlePageAuditFaqDefaults);

export function mergeSinglePageAuditFaqs(cms: FaqDoc[] | null | undefined): Faq[] {
  return mergeFaqs(cms, singlePageAuditFaqs);
}
