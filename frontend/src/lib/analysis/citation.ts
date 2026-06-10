import type { RankRow } from "@/components/analysis/common/AnalysisRankTable";
import { formatDelta, formatRate } from "@/lib/analysis/format";
import { buildBrandRankRows } from "@/lib/analysis/shared";
import type { CitationAnalysisData, CitationMentionedBrand, VisibilitySeriesPoint } from "@/types";

export const CITATION_SECTION_HEIGHT = 380;
export const CITATION_CHART_HEIGHT = 270;
export const CITATION_RANK_TABLE_HEIGHT = CITATION_SECTION_HEIGHT - 24;

export const CITATION_CHART_DESCRIPTION =
  "统计 AI 回复中各品牌来源页被引用且页面正文提及品牌的比例，按日展示引用率趋势。";

export const CITATION_DETAIL_TABS = [
  { id: "domain" as const, label: "域名" },
  { id: "url" as const, label: "URL" },
];

export const CITATION_DOMAIN_DETAIL_TABS = [
  { id: "pages" as const, label: "热门页面" },
  { id: "prompt" as const, label: "提示词" },
  { id: "topic" as const, label: "主题" },
  { id: "platform" as const, label: "平台" },
];

export type CitationOverviewData = {
  ownValue: number | null | undefined;
  prevOwnValue: number | null | undefined;
  series: VisibilitySeriesPoint[];
  previousSeries: VisibilitySeriesPoint[];
  rankRows: RankRow[];
  domains: CitationAnalysisData["domains"];
  urls: CitationAnalysisData["urls"];
};

export function buildCitationOverview(data: CitationAnalysisData | undefined): CitationOverviewData {
  const ownLabel = data?.own_label ?? "";
  return {
    ownValue: data?.citation_rate,
    prevOwnValue: data?.previous_rank.citation_share[ownLabel],
    series: data?.series ?? [],
    previousSeries: data?.previous_series ?? [],
    rankRows: data
      ? buildBrandRankRows(
          data.rank.citation_share,
          data.previous_rank.citation_share,
          ownLabel,
          formatRate,
          formatDelta,
        )
      : [],
    domains: data?.domains ?? [],
    urls: data?.urls ?? [],
  };
}

export function formatMonthlyVisits(value: number | null | undefined): string {
  if (value == null) return "—";
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(2)}K`;
  return String(value);
}

/** 是否提及本品牌：基于 LLM 提取的提及品牌列表，无分析数据时返回 null。 */
export function citationMentionsOwnBrand(
  brands: CitationMentionedBrand[],
  ownLabel: string,
  ownBrand?: string | null,
  hasBrandAnalysis?: boolean,
): boolean | null {
  if (!hasBrandAnalysis) {
    return null;
  }
  const keys = new Set([ownLabel, ownBrand].filter(Boolean).map((v) => v!.toLowerCase()));
  return brands.some((brand) => {
    const candidates = [brand.label, brand.domain].filter(Boolean).map((v) => v!.toLowerCase());
    return candidates.some((candidate) => keys.has(candidate));
  });
}
