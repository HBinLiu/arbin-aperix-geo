import type { PlatformId } from "../../platform.ts";

import type { MonitorPageSeoDefault } from "./types.ts";

export const MONITOR_PAGE_SEO: Record<PlatformId, MonitorPageSeoDefault> = {
  doubao: {
    platformId: "doubao",
    label: "豆包监测",
    path: "/platform/we-monitor-doubao/",
    titleTopic: "豆包优化 - 监控 AI 搜索排名",
    description: "掌握豆包对中文内容与字节生态的引用偏好，监测并优化品牌在豆包中的 AI 可见性。",
  },
  deepseek: {
    platformId: "deepseek",
    label: "DeepSeek 监测",
    path: "/platform/we-monitor-deepseek/",
    titleTopic: "DeepSeek 优化 - 监控 AI 搜索排名",
    description:
      "掌握 DeepSeek 对技术与学术内容的引用偏好，监测并优化品牌在 DeepSeek 中的 AI 可见性。",
  },
  qianwen: {
    platformId: "qianwen",
    label: "通义千问监测",
    path: "/platform/we-monitor-qwen/",
    titleTopic: "通义千问优化 - 监控 AI 搜索排名",
    description: "掌握通义千问对中文内容的引用偏好，优化品牌在阿里 AI 生态中的可见性。",
  },
  yuanbao: {
    platformId: "yuanbao",
    label: "腾讯元宝监测",
    path: "/platform/we-monitor-yuanbao/",
    titleTopic: "腾讯元宝优化 - 监控 AI 搜索排名",
    description:
      "掌握腾讯元宝对中文内容与微信生态的引用偏好，监测并优化品牌在元宝中的 AI 可见性。",
  },
  kimi: {
    platformId: "kimi",
    label: "Kimi 监测",
    path: "/platform/we-monitor-kimi/",
    titleTopic: "Kimi 优化 - 监控 AI 搜索排名",
    description: "掌握 Kimi 对长文本与专业内容的引用偏好，监测并优化品牌在 Kimi 中的 AI 可见性。",
  },
  ernie: {
    platformId: "ernie",
    label: "文心一言监测",
    path: "/platform/we-monitor-ernie/",
    titleTopic: "文心一言优化 - 监控 AI 搜索排名",
    description:
      "掌握文心一言对中文内容与百度搜索生态的引用偏好，监测并优化品牌在文心一言中的 AI 可见性。",
  },
};
