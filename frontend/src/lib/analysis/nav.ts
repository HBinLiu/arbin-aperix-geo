import { DASHBOARD_APP_BASE } from "@/lib/dashboard";
import type { AnalysisDimension } from "@/types";

export const ANALYSIS_DIMENSIONS: {
  id: AnalysisDimension;
  label: string;
  description: string;
}[] = [
  {
    id: "visibility",
    label: "可见度",
    description:
      "AI 回答中品牌曝光与竞争力的关键绩效指标：提供可落地的洞察，以优化品牌存在感并在生成式AI领域战胜竞争对手。",
  },
  {
    id: "prompt",
    label: "提示词",
    description: "在提示词层面分析产品可见度与表现，帮助理解 AI 搜索场景下的用户需求与转化潜力。",
  },
  {
    id: "platform",
    label: "AI 平台",
    description:
      "全景式评估品牌在主流 AI 平台上的竞争站位，提示平台间的流量分布差异与特定算法的推荐偏好。",
  },
  {
    id: "sentiment",
    label: "情感倾向",
    description:
      "AI 提及品牌时的情感倾向分析，监控品牌声誉与市场地位，洞察具体回复中的品牌表现并指导提升用户转化率。",
  },
  {
    id: "citation",
    label: "引用率",
    description:
      "包含指向您域名引用链接的品牌提及百分比。反映内容可信度和将 AI 浏览量转化为网站流量的能力。比率越高表示被引用的内容越广泛。",
  },
];

export const DEFAULT_ANALYSIS_DIMENSION: AnalysisDimension = "visibility";

export const ANALYSIS_BASE_PATH = `${DASHBOARD_APP_BASE}/analysis`;

export function parseAnalysisDimension(value: string | null | undefined): AnalysisDimension {
  if (value && ANALYSIS_DIMENSIONS.some((d) => d.id === value)) {
    return value as AnalysisDimension;
  }
  return DEFAULT_ANALYSIS_DIMENSION;
}

export function analysisDimensionPath(
  dimension: AnalysisDimension = DEFAULT_ANALYSIS_DIMENSION,
): string {
  return `${ANALYSIS_BASE_PATH}/${dimension}`;
}

export function analysisDimensionFromPathname(pathname: string): AnalysisDimension {
  const normalized = pathname.replace(/\/+$/, "");
  if (normalized === ANALYSIS_BASE_PATH) {
    return DEFAULT_ANALYSIS_DIMENSION;
  }
  if (!normalized.startsWith(`${ANALYSIS_BASE_PATH}/`)) {
    return DEFAULT_ANALYSIS_DIMENSION;
  }
  const segment = normalized.slice(`${ANALYSIS_BASE_PATH}/`.length).split("/")[0] ?? "";
  return parseAnalysisDimension(segment || null);
}

export function isAnalysisPathname(pathname: string): boolean {
  const normalized = pathname.replace(/\/+$/, "");
  return normalized === ANALYSIS_BASE_PATH || normalized.startsWith(`${ANALYSIS_BASE_PATH}/`);
}

const CITATION_DOMAIN_DETAIL_PREFIX = `${ANALYSIS_BASE_PATH}/citation/`;

export function citationDomainDetailPath(domain: string): string {
  return `${CITATION_DOMAIN_DETAIL_PREFIX}${encodeURIComponent(domain)}`;
}

export function citationDomainFromPathname(pathname: string): string | null {
  const normalized = pathname.replace(/\/+$/, "");
  if (normalized === `${ANALYSIS_BASE_PATH}/citation`) {
    return null;
  }
  if (!normalized.startsWith(CITATION_DOMAIN_DETAIL_PREFIX)) {
    return null;
  }
  const encoded = normalized.slice(CITATION_DOMAIN_DETAIL_PREFIX.length).split("/")[0] ?? "";
  if (!encoded) {
    return null;
  }
  try {
    return decodeURIComponent(encoded).trim().toLowerCase();
  } catch {
    return encoded.trim().toLowerCase();
  }
}

export function isCitationDomainDetailPathname(pathname: string): boolean {
  return citationDomainFromPathname(pathname) != null;
}

const PROMPT_DETAIL_PREFIX = `${ANALYSIS_BASE_PATH}/prompt/`;

export function promptDetailPath(promptId: string): string {
  return `${PROMPT_DETAIL_PREFIX}${encodeURIComponent(promptId)}`;
}

export function promptIdFromPathname(pathname: string): string | null {
  const normalized = pathname.replace(/\/+$/, "");
  if (normalized === `${ANALYSIS_BASE_PATH}/prompt`) {
    return null;
  }
  if (!normalized.startsWith(PROMPT_DETAIL_PREFIX)) {
    return null;
  }
  const encoded = normalized.slice(PROMPT_DETAIL_PREFIX.length).split("/")[0] ?? "";
  if (!encoded) {
    return null;
  }
  try {
    return decodeURIComponent(encoded).trim();
  } catch {
    return encoded.trim();
  }
}

export function isPromptDetailPathname(pathname: string): boolean {
  return promptIdFromPathname(pathname) != null;
}
