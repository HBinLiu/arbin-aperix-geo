import type { RankRow } from "@/components/analysis/common/AnalysisRankTable";
import { formatDelta, formatRate } from "@/lib/analysis/format";
import { buildBrandRankRows } from "@/lib/analysis/shared";
import type { CitationAnalysisData, VisibilitySeriesPoint } from "@/types";

export const CITATION_SECTION_HEIGHT = 380;
export const CITATION_CHART_HEIGHT = 270;
export const CITATION_RANK_TABLE_HEIGHT = CITATION_SECTION_HEIGHT - 24;

export const CITATION_CHART_DESCRIPTION =
  "统计 AI 回复中引用各品牌域名或页面的比例，按日展示引用率趋势。";

export const CITATION_DETAIL_TABS = [
  { id: "domain" as const, label: "域名" },
  { id: "url" as const, label: "URL" },
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
