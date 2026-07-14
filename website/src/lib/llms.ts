import { homeFaqs, type Faq } from "@/lib/home";
import { pricingFaqSection, pricingFaqs } from "@/lib/pricing";
import {
  aboutSeo,
  contactSeo,
  researchSeo,
  newsSeo,
  blogSeo,
  homeSeo,
  platformAnswerSeo,
  platformContentSeo,
  platformMonitorSeo,
  platformPromptSeo,
  platformTopicSeo,
  pricingSeo,
} from "@/lib/seo";
import { MONITOR_SLUGS } from "@/lib/platform/monitor";
import type { PlatformId } from "@shared/platform";
import { siteConfig } from "@site";
import { appLinks } from "@/lib/app-links";

type LlmsEntry = {
  path: string;
  label: string;
  description: string;
};

function pageHref(site: URL, path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  if (path === "/") return new URL("/", site).href;
  const [pathname, hash = ""] = path.split("#");
  if (/\.[a-z0-9]+$/i.test(pathname)) {
    return new URL(path, site).href;
  }
  const normalized = pathname.endsWith("/") ? pathname : `${pathname}/`;
  const href = hash ? `${normalized}#${hash}` : normalized;
  return new URL(href, site).href;
}

function linkLine(site: URL, entry: LlmsEntry): string {
  return `- [${entry.label}](${pageHref(site, entry.path)}): ${entry.description}`;
}

function faqTopicSummary(questions: string[]): string {
  return questions.join("、");
}

const PLATFORM_PAGES: LlmsEntry[] = [
  {
    path: "/platform/answer-engine-insights",
    label: "回答引擎洞察",
    description: platformAnswerSeo.description,
  },
  {
    path: "/platform/find-topics-ideas",
    label: "发现机会与差距",
    description: platformTopicSeo.description,
  },
  {
    path: "/platform/prompt-volumes-explorer",
    label: "提示词查询探索",
    description: platformPromptSeo.description,
  },
  {
    path: "/platform/content-creation-optimization",
    label: "内容创作与优化",
    description: platformContentSeo.description,
  },
];

const MONITOR_PAGES: LlmsEntry[] = (Object.entries(MONITOR_SLUGS) as [PlatformId, string][]).map(
  ([platformId, slug]) => {
    const seo = platformMonitorSeo[platformId];
    return {
      path: `/platform/${slug}`,
      label: seo.title.split(" | ")[0] ?? seo.title,
      description: seo.description,
    };
  },
);

const PLATFORM_FAQ_PAGES: LlmsEntry[] = [
  ...PLATFORM_PAGES.map((entry) => ({
    ...entry,
    path: `${entry.path}#faq`,
    description: `平台能力页 FAQ：${entry.description}`,
  })),
  ...MONITOR_PAGES.map((entry) => ({
    ...entry,
    path: `${entry.path}#faq`,
    description: `平台监测页 FAQ：${entry.description}`,
  })),
];

/** 面向 AI 爬虫的 llms.txt 正文（遵循 llmstxt.org：H2 区块均为链接列表） */
export function buildLlmsTxt(site: URL, faqs: Faq[] = homeFaqs): string {
  const corePages: LlmsEntry[] = [
    { path: "/", label: "首页", description: homeSeo.description },
    { path: "/pricing", label: "定价", description: pricingSeo.description },
    { path: "/about", label: "关于我们", description: aboutSeo.description },
    { path: "/contact", label: "联系我们", description: contactSeo.description },
    { path: "/research", label: "研究", description: researchSeo.description },
    { path: "/news", label: "新闻", description: newsSeo.description },
    { path: "/blog", label: "博客", description: blogSeo.description },
  ];

  const homeFaqLink: LlmsEntry = {
    path: "/#faq",
    label: "首页常见问题",
    description: faqTopicSummary(faqs.map((faq) => faq.question)),
  };

  const pricingFaqLink: LlmsEntry = {
    path: "/pricing/#faq",
    label: pricingFaqSection.title,
    description: `${pricingFaqSection.subtitle} 涵盖 ${faqTopicSummary(pricingFaqs.map((faq) => faq.question))}`,
  };

  return [
    `# ${siteConfig.name}`,
    "",
    `> ${siteConfig.description}。${homeSeo.description}`,
    "",
    "## 核心页面",
    "",
    ...corePages.map((entry) => linkLine(site, entry)),
    "",
    "## 平台能力",
    "",
    ...PLATFORM_PAGES.map((entry) => linkLine(site, entry)),
    "",
    "## AI 平台监测",
    "",
    ...MONITOR_PAGES.map((entry) => linkLine(site, entry)),
    "",
    "## 常见问题",
    "",
    linkLine(site, homeFaqLink),
    "",
    "## 定价常见问题",
    "",
    linkLine(site, pricingFaqLink),
    "",
    "## 平台 FAQ",
    "",
    ...PLATFORM_FAQ_PAGES.map((entry) => linkLine(site, entry)),
    "",
    "## 可选",
    "",
    `- [控制台](${pageHref(site, appLinks.register)}): 注册并开始 GEO 监测`,
    `- [Sitemap](${pageHref(site, "/sitemap-index.xml")}): 全站 URL 索引`,
  ].join("\n");
}
