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
    description: "各提示词下的可见度表现，帮助识别高价值质询场景。",
  },
  {
    id: "platform",
    label: "AI 平台",
    description: "不同大模型渠道下的品牌可见度与提及强度对比。",
  },
  {
    id: "sentiment",
    label: "情感倾向",
    description: "AI 回答中对自有品牌的情感评分与分布趋势。",
  },
  {
    id: "citation",
    label: "引用率",
    description: "回答中引用品牌相关来源的比例，衡量权威背书程度。",
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
