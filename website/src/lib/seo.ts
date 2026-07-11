import type { PlatformId } from "@shared/platform";
import { siteConfig } from "@site";
import { resolveSiteCopy, sitePageTitle } from "@/lib/site";

export type PageSeo = {
  title: string;
  description: string;
  canonicalPath?: string;
  image?: string;
  type?: "website" | "article";
  noindex?: boolean;
};

export type ResolvedPageMeta = {
  title: string;
  description: string;
  canonical: string;
  image: string;
  type: "website" | "article";
  siteName: string;
  noindex: boolean;
};

function normalizePathname(pathname: string): string {
  if (pathname === "/" || pathname.endsWith("/")) return pathname;
  return `${pathname}/`;
}

function toAbsoluteUrl(pathOrUrl: string, base: URL): string {
  if (pathOrUrl.startsWith("http://") || pathOrUrl.startsWith("https://")) {
    return pathOrUrl;
  }
  return new URL(pathOrUrl, base).href;
}

/** CMS / 运行时覆盖：空字段回退到 defaults */
export function mergePageSeo(base: PageSeo, override?: Partial<PageSeo> | null): PageSeo {
  if (!override) return base;
  return {
    ...base,
    ...override,
    title: resolveSiteCopy(override.title?.trim() || base.title),
    description: resolveSiteCopy(override.description?.trim() || base.description),
  };
}

/** 将 PageSeo 解析为 head 所需的 canonical / OG / Twitter 字段；site 来自 Astro.site（astro.config site） */
export function resolvePageMeta(seo: PageSeo, site: URL, pathname: string): ResolvedPageMeta {
  const canonical = toAbsoluteUrl(normalizePathname(seo.canonicalPath ?? pathname), site);

  return {
    title: seo.title,
    description: seo.description,
    canonical,
    image: toAbsoluteUrl(seo.image ?? siteConfig.ogImage, site),
    type: seo.type ?? "website",
    siteName: siteConfig.name,
    noindex: seo.noindex ?? false,
  };
}

/** 全站 `<title>` 格式：`{页面主题} | {品牌名}` */
function pageTitle(topic: string): string {
  return sitePageTitle(topic);
}

/** 首页 */
export const homeSeo: PageSeo = {
  title: pageTitle("数据驱动的 GEO 品牌可见性监测平台"),
  description: resolveSiteCopy(
    "{{name}} 专注于生成式引擎优化，覆盖国内主流大模型平台，监测品牌在 AI 中的可见度以及竞争洞察分析。不止于 GEO 审计，更提供数据驱动的 GEO 增长策略、AI 内容创作引擎与优化服务。",
  ),
};

/** 关于我们 */
export const aboutSeo: PageSeo = {
  title: pageTitle("关于我们"),
  description: resolveSiteCopy(
    "{{name}} 是一家专注于生成式引擎优化的公司，致力于帮助品牌建立真实的 AI 信任与影响力。我们连接 SEO 与 GEO，让每个企业都能获得 AI 可见性。了解我们的故事。",
  ),
};

/** 定价 */
export const pricingSeo: PageSeo = {
  title: pageTitle("定价方案"),
  description:
    "覆盖国内主流 AI 平台的订阅方案。个人版、专业版、旗舰版与企业版，按月/季/年灵活订阅。",
};

/** 平台能力页 */
export const platformAnswerSeo: PageSeo = {
  title: pageTitle("AI 可见度与竞争洞察分析"),
  description:
    "基于真实 AI 回答与 Prompt，分析品牌在 AI 搜索中的可见度、声量份额与引用结构，识别竞争差距与高价值优化机会。",
};

export const platformTopicSeo: PageSeo = {
  title: pageTitle("AI 增长机会与信源分析"),
  description:
    "基于真实提示词与引用结构，识别尚未覆盖的高价值场景与信源机会，将 AI 回答逻辑转化为可执行的 GEO 增长策略。",
};

export const platformPromptSeo: PageSeo = {
  title: pageTitle("提示词与查询扇出分析"),
  description:
    "分析真实提示词与查询扇出，洞察 AI 如何拆解用户需求，识别高价值问题与趋势变化，优化内容与 GEO 投入优先级。",
};

export const platformContentSeo: PageSeo = {
  title: pageTitle("AI 智能内容创作引擎"),
  description:
    "创作针对搜索引擎和 AI 平台创作的高质量文章。内置 SEO/GEO 优化的内容简报、大纲和完整文章。",
};

/** 各 AI 平台监测落地页 */
export const platformMonitorSeo: Record<PlatformId, PageSeo> = {
  doubao: {
    title: pageTitle("豆包优化 - 监控 AI 搜索排名"),
    description:
      "掌握豆包对中文内容与字节生态的引用偏好，监测并优化品牌在豆包中的 AI 可见性。",
  },
  deepseek: {
    title: pageTitle("DeepSeek 优化 - 监控 AI 搜索排名"),
    description:
      "掌握 DeepSeek 对技术与学术内容的引用偏好，监测并优化品牌在 DeepSeek 中的 AI 可见性。",
  },
  qianwen: {
    title: pageTitle("通义千问优化 - 监控 AI 搜索排名"),
    description: "掌握通义千问对中文内容的引用偏好，优化品牌在阿里 AI 生态中的可见性。",
  },
  yuanbao: {
    title: pageTitle("腾讯元宝优化 - 监控 AI 搜索排名"),
    description:
      "掌握腾讯元宝对中文内容与微信生态的引用偏好，监测并优化品牌在元宝中的 AI 可见性。",
  },
  kimi: {
    title: pageTitle("Kimi 优化 - 监控 AI 搜索排名"),
    description:
      "掌握 Kimi 对长文本与专业内容的引用偏好，监测并优化品牌在 Kimi 中的 AI 可见性。",
  },
  ernie: {
    title: pageTitle("文心一言优化 - 监控 AI 搜索排名"),
    description:
      "掌握文心一言对中文内容与百度搜索生态的引用偏好，监测并优化品牌在文心一言中的 AI 可见性。",
  },
};
