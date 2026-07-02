import type { RankRow } from "@/components/analysis/common/AnalysisRankTable";
import { formatDelta, formatRate } from "@/lib/analysis/format";
import { entityRankFlags } from "@/lib/analysis/entities";
import type {
  AnalysisEntityRef,
  CitationAnalysisData,
  CitationMentionedBrand,
  VisibilitySeriesPoint,
} from "@/types";

export const CITATION_SECTION_HEIGHT = 380;
export const CITATION_RANK_TABLE_HEIGHT = CITATION_SECTION_HEIGHT - 24;

export const CITATION_CHART_DESCRIPTION =
  "包含指向您域名的来源链接的品牌提及百分比。反映内容可信度和将 AI 浏览量转化为网站流量的能力。比率越高表示被引用的内容越广泛。";

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
};

export function buildCitationRankRows(
  rows: CitationAnalysisData["rank_table"] | undefined,
  entities: AnalysisEntityRef[],
  focusEntityId: string | undefined,
): RankRow[] {
  return (rows ?? []).map((row) => {
    const { isOwn, isFocus } = entityRankFlags(entities, row.id, focusEntityId);
    return {
      id: row.id,
      label: row.label,
      domain: row.domain || null,
      value: formatRate(row.cur_value),
      valueNum: row.cur_value ?? undefined,
      delta: formatDelta(row.cur_value, row.pre_value),
      deltaSortNum:
        row.cur_value != null && row.pre_value != null ? row.cur_value - row.pre_value : null,
      isOwn,
      isFocus,
    };
  });
}

export function buildCitationOverview(
  data: CitationAnalysisData | undefined,
  entities: AnalysisEntityRef[],
  focusEntityId: string | undefined,
): CitationOverviewData {
  return {
    ownValue: data?.citation_rate,
    prevOwnValue: data?.citation_previous,
    series: data?.series ?? [],
    previousSeries: data?.previous_series ?? [],
    rankRows: buildCitationRankRows(data?.rank_table, entities, focusEntityId),
  };
}

export function formatMonthlyVisits(value: number | null | undefined): string {
  if (value == null) return "—";
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(2)}K`;
  return String(value);
}

/** 过滤 SSR 模板占位 title（如 {{content.leadTitle}}），无有效 title 时回退到 URL。 */
const TEMPLATE_TITLE_RE = /\{\{[^}]+\}\}/;

export function citationUrlDisplayTitle(title: string | null | undefined, url: string): string {
  const cleaned = (title ?? "").trim();
  if (cleaned && !TEMPLATE_TITLE_RE.test(cleaned)) {
    return cleaned;
  }
  return url;
}

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
