import { brandDisplayLabel } from "@/lib/brand/display";
import {
  formatRate,
  formatRankMetric,
  formatSentimentScore,
} from "@/lib/analysis/format";
import type { BrandItem, BrandSortField } from "@/types";
import type { ReactNode } from "react";

export type BrandSortColumn =
  | "visibility"
  | "shareVoice"
  | "mention"
  | "averageRank"
  | "citation"
  | "sentiment";

export type BrandRow = {
  brandId: string;
  label: string;
  domain: string | null;
  icon?: ReactNode;
  visibility: string;
  shareVoice: string;
  mention: string;
  averageRank: string;
  citationRate: string;
  sentiment: string;
  sentimentLabel: string | null;
};

function formatShareVoice(value: number | null | undefined): string {
  if (value == null || value === 0) return "—";
  return formatRate(value);
}

function formatAverageRank(value: number | null | undefined): string {
  if (value == null) return "—";
  return formatRankMetric(value);
}

function formatSentiment(value: number | null | undefined): string {
  if (value == null) return "0.0";
  return formatSentimentScore(value);
}

export function buildBrandRows(items: BrandItem[]): BrandRow[] {
  return items.map((item) => {
    const displayName = brandDisplayLabel(item);
    const domain = item.domain.trim() || null;
    return {
      brandId: item.brand_id,
      label: displayName,
      domain,
      visibility: formatRate(item.visibility_rate ?? 0),
      shareVoice: formatShareVoice(item.share_voice),
      mention: formatRate(item.mention_rate ?? 0),
      averageRank: formatAverageRank(item.average_rank),
      citationRate: formatRate(item.citation_rate ?? 0),
      sentiment: formatSentiment(item.sentiment_score),
      sentimentLabel: item.sentiment_label ?? null,
    };
  });
}

const SORT_COLUMN_TO_API: Record<BrandSortColumn, BrandSortField> = {
  visibility: "visibility_rate",
  shareVoice: "share_voice",
  mention: "mention_rate",
  averageRank: "average_rank",
  citation: "citation_rate",
  sentiment: "sentiment_score",
};

export function brandSortToApiField(
  column: BrandSortColumn,
  dir: "asc" | "desc",
): { sortBy: BrandSortField; order: "asc" | "desc" } {
  return { sortBy: SORT_COLUMN_TO_API[column], order: dir };
}

export const BRAND_COLUMNS: {
  id: BrandSortColumn;
  label: string;
  higherIsBetter: boolean;
  width: string;
}[] = [
  { id: "visibility", label: "可见度", higherIsBetter: true, width: "11%" },
  { id: "shareVoice", label: "声量份额", higherIsBetter: true, width: "11%" },
  { id: "mention", label: "AI 提及", higherIsBetter: true, width: "11%" },
  { id: "averageRank", label: "平均排名", higherIsBetter: false, width: "11%" },
  { id: "citation", label: "引用率", higherIsBetter: true, width: "11%" },
  { id: "sentiment", label: "情感倾向分数", higherIsBetter: true, width: "11%" },
];

export const BRAND_MIN_WIDTH = 1080;
