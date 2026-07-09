import type { PageSeo } from "@/lib/seo";
import type { FaqItem } from "@/lib/home";
import type { PlatformId } from "@shared/platform";
import { PLATFORMS } from "@shared/platform";

export type MonitorPreferences = {
  primary: string[];
  secondary: string[];
  avoid: string[];
};

export type MonitorContent = {
  platformId: PlatformId;
  slug: string;
  displayName: string;
  seo: PageSeo;
  h1: string;
  intro: string;
  mechanismTitle: string;
  mechanismContent: string;
  preferences: MonitorPreferences;
  strategyTitle: string;
  strategyContent: string;
  trustNote: string;
};

export const MONITOR_SLUGS: Record<PlatformId, string> = {
  doubao: "we-monitor-doubao",
  deepseek: "we-monitor-deepseek",
  qianwen: "we-monitor-qwen",
  yuanbao: "we-monitor-yuanbao",
  kimi: "we-monitor-kimi",
  ernie: "we-monitor-ernie",
};

const SLUG_TO_PLATFORM_ID = Object.fromEntries(
  Object.entries(MONITOR_SLUGS).map(([id, slug]) => [slug, id as PlatformId]),
) as Record<string, PlatformId>;

export const MONITOR_STEPS = [
  {
    title: "连接您的品牌",
    description: "告诉我们您的品牌、产品以及需要监测的竞争对手。",
    icon: "zap",
  },
  {
    title: "监测 AI 响应",
    description: "我们持续追踪此 AI 平台如何讨论并推荐您的品牌。",
    icon: "target",
  },
  {
    title: "优化可见性",
    description: "获得可执行的洞察，以改善您在 AI 中的品牌呈现。",
    icon: "chart",
  },
] as const;

export function monitorHref(platformId: PlatformId): string {
  return `/platform/${MONITOR_SLUGS[platformId]}`;
}

export function resolveMonitorSlug(slug: string): PlatformId | null {
  return SLUG_TO_PLATFORM_ID[slug] ?? null;
}

export function monitorSlugs(): string[] {
  return Object.values(MONITOR_SLUGS);
}

function monitorFaqItems(platformName: string): FaqItem[] {
  return [
    {
      question: "监测是如何进行的？",
      answer: "我们使用与行业相关的提示词持续向 AI 平台发起查询，并追踪品牌在回答中被提及、引用和推荐的情况。",
    },
    {
      question: "数据更新频率是多久？",
      answer: "我们的监测每天运行，对于 AI 平台讨论您品牌的重大变化，我们会提供实时提醒。",
    },
    {
      question: "我可以与竞争对手进行对比吗？",
      answer: "可以，我们的竞争情报功能可以展示您在所有已监测平台中，与竞争对手在 AI 可见性方面的对比情况。",
    },
  ];
}

export function monitorFaqs(platformId: PlatformId): FaqItem[] {
  const content = MONITOR_CONTENT[platformId];
  return monitorFaqItems(content.displayName);
}

const MONITOR_CONTENT: Record<PlatformId, Omit<MonitorContent, "platformId" | "slug">> = {
  doubao: {
    displayName: "豆包",
    seo: {
      title: "豆包优化 - 监控 AI 搜索排名",
      description:
        "掌握豆包对中文内容与字节生态的引用偏好，监测并优化品牌在豆包中的 AI 可见性。",
    },
    h1: "豆包 GEO 策略：引用机制与优化",
    intro: "掌握豆包对中文内容与字节系生态的引用偏好，优化品牌在字节 AI 生态中的可见性。",
    mechanismTitle: "引用机制基础",
    mechanismContent:
      "豆包依托字节系内容与搜索数据，在回答中更倾向引用结构清晰、时效性强、与用户需求高度匹配的中文内容，并重视官方来源与可验证的产品信息。",
    preferences: {
      primary: ["官方品牌站点与产品文档", "高质量中文原创内容", "权威媒体与行业报告"],
      secondary: ["用户评价与案例研究", "结构化 FAQ 与帮助中心"],
      avoid: ["低质量采集或洗稿内容", "过时或不一致的产品信息"],
    },
    strategyTitle: "差异化 GEO 策略",
    strategyContent:
      "豆包与字节内容生态深度联动。进行 GEO 优化时，应确保品牌内容结构清晰、更新及时，覆盖用户高频提问场景，并在官网沉淀可被引用的权威页面。",
    trustNote: "根据豆包大模型公开文档及中文 AI 行业实践数据总结。",
  },
  deepseek: {
    displayName: "DeepSeek",
    seo: {
      title: "DeepSeek 优化 - 监控 AI 搜索排名",
      description:
        "掌握 DeepSeek 对技术与学术内容的引用偏好，监测并优化品牌在 DeepSeek 中的 AI 可见性。",
    },
    h1: "DeepSeek GEO 策略：引用机制与优化",
    intro: "掌握 DeepSeek 对技术和学术内容的引用偏好，优化品牌在中文 AI 生态中的可见性。",
    mechanismTitle: "引用机制基础",
    mechanismContent:
      "DeepSeek 在技术与推理类问题中表现突出，引用机制偏向结构完整的技术文档、可验证的代码示例，以及具备清晰论证逻辑的权威内容。",
    preferences: {
      primary: ["技术文档与 API 参考", "可运行的代码示例", "学术论文与技术博客"],
      secondary: ["开发者社区讨论", "GitHub 开源项目说明"],
      avoid: ["陈旧的技术文档", "无法验证的主观断言"],
    },
    strategyTitle: "差异化 GEO 策略",
    strategyContent:
      "DeepSeek 擅长技术推理。进行 GEO 优化时，建议编写全面的技术文档，包含可运行的代码示例，并保持 API 参考的实时更新，以匹配其引用偏好。",
    trustNote: "根据 DeepSeek 模型文档及中文 AI 行业实践数据总结。",
  },
  qianwen: {
    displayName: "通义千问",
    seo: {
      title: "通义千问优化 - 监控 AI 搜索排名",
      description: "掌握通义千问对中文内容的引用偏好，优化品牌在阿里 AI 生态中的可见性。",
    },
    h1: "通义千问 GEO 策略：引用机制与优化",
    intro: "掌握通义千问对中文内容的引用偏好，优化品牌在阿里 AI 生态中的可见性。",
    mechanismTitle: "引用机制基础",
    mechanismContent:
      "通义千问具有强大的中文理解能力，并与阿里的电商和企业生态深度整合。其引用机制强调电商相关性、中文内容质量以及商业应用场景。",
    preferences: {
      primary: ["阿里生态验证内容", "高质量中文商业内容", "电商产品文档"],
      secondary: ["中文行业报告", "淘宝/天猫经过验证的用户评价"],
      avoid: ["低质量的翻译内容", "未经验证的卖家信息"],
    },
    strategyTitle: "差异化 GEO 策略",
    strategyContent:
      "通义千问与阿里电商深度集成。进行 GEO 优化时，应确保高质量的中文内容产出，在相关领域与阿里平台进行联动，并强调商业价值主张，以匹配其引用偏好。",
    trustNote: "根据阿里云通义千问文档及中文 AI 行业实践数据总结。",
  },
  yuanbao: {
    displayName: "腾讯元宝",
    seo: {
      title: "腾讯元宝优化 - 监控 AI 搜索排名",
      description:
        "掌握腾讯元宝对中文内容与微信生态的引用偏好，监测并优化品牌在元宝中的 AI 可见性。",
    },
    h1: "腾讯元宝 GEO 策略：引用机制与优化",
    intro: "掌握腾讯元宝对中文内容与社交生态的引用偏好，优化品牌在腾讯 AI 生态中的可见性。",
    mechanismTitle: "引用机制基础",
    mechanismContent:
      "腾讯元宝深度整合微信与腾讯内容生态，在引用时更重视中文原创质量、品牌可信度，以及与用户生活场景相关的高价值内容。",
    preferences: {
      primary: ["官方品牌官网与产品页", "高质量中文原创内容", "微信公众号权威文章"],
      secondary: ["行业媒体深度报道", "用户评价与案例"],
      avoid: ["营销堆砌的软文", "来源不明的第三方转载"],
    },
    strategyTitle: "差异化 GEO 策略",
    strategyContent:
      "元宝与腾讯社交生态紧密相连。进行 GEO 优化时，应同步建设官网权威内容与公众号矩阵，确保品牌信息在各渠道一致，并覆盖用户常见决策问题。",
    trustNote: "根据腾讯元宝公开能力说明及中文 AI 行业实践数据总结。",
  },
  kimi: {
    displayName: "Kimi",
    seo: {
      title: "Kimi 优化 - 监控 AI 搜索排名",
      description:
        "掌握 Kimi 对长文本与专业内容的引用偏好，监测并优化品牌在 Kimi 中的 AI 可见性。",
    },
    h1: "Kimi GEO 策略：引用机制与优化",
    intro: "掌握 Kimi 对长文本与专业内容的引用偏好，优化品牌在月之暗面 AI 生态中的可见性。",
    mechanismTitle: "引用机制基础",
    mechanismContent:
      "Kimi 擅长长上下文理解与专业领域问答，引用机制倾向于结构严谨、信息密度高、来源可追溯的深度内容，尤其重视报告类与指南类材料。",
    preferences: {
      primary: ["深度行业报告与白皮书", "结构化的产品文档", "权威媒体调研"],
      secondary: ["专业博客与技术解读", "官方 FAQ 与帮助中心"],
      avoid: ["碎片化且无出处的信息", "过度营销化的宣传文案"],
    },
    strategyTitle: "差异化 GEO 策略",
    strategyContent:
      "Kimi 适合承载长文本引用。进行 GEO 优化时，建议产出系统性行业指南与品牌白皮书，明确章节结构与数据来源，提升被引用与推荐的概率。",
    trustNote: "根据 Kimi 产品能力说明及中文 AI 行业实践数据总结。",
  },
  ernie: {
    displayName: "文心一言",
    seo: {
      title: "文心一言优化 - 监控 AI 搜索排名",
      description:
        "掌握文心一言对中文内容与百度搜索生态的引用偏好，监测并优化品牌在文心一言中的 AI 可见性。",
    },
    h1: "文心一言 GEO 策略：引用机制与优化",
    intro: "掌握文心一言对中文内容与搜索生态的引用偏好，优化品牌在百度 AI 生态中的可见性。",
    mechanismTitle: "引用机制基础",
    mechanismContent:
      "文心一言与百度搜索及百度内容生态深度整合，引用时更重视中文内容质量、页面权威度，以及与搜索意图高度匹配的结构化信息。",
    preferences: {
      primary: ["官方网站与权威产品页", "高质量中文原创内容", "百度百科与结构化词条"],
      secondary: ["行业垂直媒体", "用户评价与第三方评测"],
      avoid: ["低质量采集站内容", "关键词堆砌的 SEO 页面"],
    },
    strategyTitle: "差异化 GEO 策略",
    strategyContent:
      "文心一言与百度生态强绑定。进行 GEO 优化时，应同步提升官网内容质量与搜索表现，完善结构化数据，并确保品牌信息在全网渠道保持一致。",
    trustNote: "根据百度文心一言公开文档及中文 AI 行业实践数据总结。",
  },
};

export function getMonitorContent(platformId: PlatformId): MonitorContent {
  const entry = MONITOR_CONTENT[platformId];
  return {
    platformId,
    slug: MONITOR_SLUGS[platformId],
    ...entry,
  };
}

export function getAllMonitorPages(): MonitorContent[] {
  return PLATFORMS.map((platform) => getMonitorContent(platform.id));
}

export function getMonitorContentBySlug(slug: string): MonitorContent | null {
  const platformId = resolveMonitorSlug(slug);
  if (!platformId) return null;
  return getMonitorContent(platformId);
}
