import { brandRowLabel } from "@/lib/brand/hoverRow";
import { formatRate, formatSentimentScore } from "@/lib/analysis/format";
import { sentimentDisplayLabel } from "@/lib/analysis/sentiment";
import type { RankBoardRow } from "@/lib/dashboard/rank";
import type { CompetitorItem, RankBoardItem } from "@/types";

export type BrandGeoMetrics = {
  visibility: string;
  citationRate: string;
  shareVoice: string;
  /** 情感展示文案（正面/中立/负面），无数据时为 — */
  sentiment: string;
  /** 情感分值，用于 DotBadge */
  sentimentScore: string | null;
  /** 后端 sentiment_label（positive/neutral/negative） */
  sentimentLabel: string | null;
};

export const EMPTY_BRAND_GEO_METRICS: BrandGeoMetrics = {
  visibility: "—",
  citationRate: "—",
  shareVoice: "—",
  sentiment: "—",
  sentimentScore: null,
  sentimentLabel: null,
};

function normalize(value: string | null | undefined): string {
  return (value ?? "").trim().toLowerCase();
}

function matchNames(row: CompetitorItem, label: string, item: RankBoardItem): boolean {
  const targets = new Set(
    [label, brandRowLabel(row), row.brand, row.domain, ...(row.aliases ?? [])]
      .map(normalize)
      .filter(Boolean),
  );
  const sources = [item.brand, item.label, item.domain].map(normalize).filter(Boolean);
  return sources.some((name) => targets.has(name));
}

/** 在 rank 接口结果中按悬停卡 row / 展示名查找对应实体。 */
export function findRankItemForHover(
  items: RankBoardItem[],
  row: CompetitorItem,
  displayLabel?: string,
): RankBoardItem | undefined {
  const label = displayLabel ?? brandRowLabel(row);
  return items.find((item) => matchNames(row, label, item));
}

export function formatBrandGeoMetrics(item: RankBoardItem): BrandGeoMetrics {
  const shareVoice = item.share_voice;
  const sentimentLabel = sentimentDisplayLabel(item.sentiment_label);

  return {
    visibility: formatRate(item.visibility_rate),
    citationRate: formatRate(item.citation_rate),
    shareVoice: shareVoice == null || shareVoice === 0 ? "—" : formatRate(shareVoice),
    sentiment: sentimentLabel !== "-" ? sentimentLabel : "—",
    sentimentScore:
      item.sentiment_score != null ? formatSentimentScore(item.sentiment_score) : null,
    sentimentLabel: item.sentiment_label ?? null,
  };
}

export function brandGeoMetricsFromRankItems(
  items: RankBoardItem[],
  row: CompetitorItem,
  displayLabel?: string,
): BrandGeoMetrics {
  const item = findRankItemForHover(items, row, displayLabel);
  if (!item) return EMPTY_BRAND_GEO_METRICS;
  return formatBrandGeoMetrics(item);
}

/** 排行榜行 → 悬停卡四指标（与表格展示一致）。 */
export function rankBoardRowToBrandGeoMetrics(row: RankBoardRow): BrandGeoMetrics {
  const sentiment = sentimentDisplayLabel(row.sentimentLabel);
  return {
    visibility: row.visibility,
    citationRate: row.citationRate,
    shareVoice: row.shareVoice,
    sentiment: sentiment !== "-" ? sentiment : "—",
    sentimentScore: row.sentimentNum != null ? row.sentiment : null,
    sentimentLabel: row.sentimentLabel,
  };
}
