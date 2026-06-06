import {
  formatRate,
  formatRankMetric,
  formatSentimentScore,
} from "@/lib/analysis/format";
import type { RankData } from "@/types";

export type BrandLeaderboardSortColumn =
  | "visibility"
  | "shareVoice"
  | "mention"
  | "averageRank"
  | "citation"
  | "sentiment";

export type BrandLeaderboardRow = {
  id: string;
  label: string;
  isOwn: boolean;
  visibility: string;
  visibilityNum: number;
  shareVoice: string;
  shareVoiceNum: number | null;
  mention: string;
  mentionNum: number;
  averageRank: string;
  averageRankNum: number | null;
  citationRate: string;
  citationNum: number;
  sentiment: string;
  sentimentNum: number | null;
};

function formatShareVoice(value: number | null | undefined): { text: string; num: number | null } {
  if (value == null || value === 0) return { text: "—", num: null };
  return { text: formatRate(value), num: value };
}

function formatAverageRank(value: number | null | undefined): {
  text: string;
  num: number | null;
} {
  if (value == null) return { text: "—", num: null };
  return { text: formatRankMetric(value), num: value };
}

function formatSentiment(value: number | null | undefined): {
  text: string;
  num: number | null;
} {
  if (value == null) return { text: "0.0", num: 0 };
  return { text: formatSentimentScore(value), num: value };
}

export function buildBrandLeaderboardRows(data: RankData): BrandLeaderboardRow[] {
  const labels = Object.keys(data.visibility_share).sort(
    (a, b) => (data.visibility_share[b] ?? 0) - (data.visibility_share[a] ?? 0),
  );

  return labels.map((label) => {
    const visibilityNum = data.visibility_share[label] ?? 0;
    const shareVoice = formatShareVoice(data.share_voice[label]);
    const mentionNum = data.mention_share[label] ?? 0;
    const averageRank = formatAverageRank(data.average_rank[label]);
    const citationNum = data.citation_share?.[label] ?? 0;
    const sentiment = formatSentiment(data.sentiment_score?.[label]);

    return {
      id: label,
      label,
      isOwn: label === data.own_label,
      visibility: formatRate(visibilityNum),
      visibilityNum,
      shareVoice: shareVoice.text,
      shareVoiceNum: shareVoice.num,
      mention: formatRate(mentionNum),
      mentionNum,
      averageRank: averageRank.text,
      averageRankNum: averageRank.num,
      citationRate: formatRate(citationNum),
      citationNum,
      sentiment: sentiment.text,
      sentimentNum: sentiment.num,
    };
  });
}

export const BRAND_LEADERBOARD_COLUMNS: {
  id: BrandLeaderboardSortColumn;
  label: string;
  description?: string;
  /** 数值越大越好；平均排名为 false（越小越好） */
  higherIsBetter: boolean;
  width: string;
}[] = [
  {
    id: "visibility",
    label: "可见度",
    description: "在所选时间窗内，至少提及一次该品牌的 AI 回复占全部成功回复的比例。",
    higherIsBetter: true,
    width: "11%",
  },
  {
    id: "shareVoice",
    label: "声量份额",
    description: "品牌在 AI 内容中的提及份额比例，反映 AI 讨论该品牌相对竞品的倾向。",
    higherIsBetter: true,
    width: "11%",
  },
  {
    id: "mention",
    label: "AI 提及",
    description: "AI 回复正文中品牌提及的频率占比，反映品牌在内容中的存在感。",
    higherIsBetter: true,
    width: "11%",
  },
  {
    id: "averageRank",
    label: "平均排名",
    description: "品牌在 AI 生成回答正文中的平均提及排名，数值越小表示越靠前。",
    higherIsBetter: false,
    width: "11%",
  },
  {
    id: "citation",
    label: "引用率",
    description: "AI 回复中引用该品牌域名或页面的比例。",
    higherIsBetter: true,
    width: "11%",
  },
  {
    id: "sentiment",
    label: "情感倾向分数",
    description: "AI 在提及该品牌时的平均情感得分，0–100 越高越正向。",
    higherIsBetter: true,
    width: "13%",
  },
];

export const BRAND_LEADERBOARD_MIN_WIDTH = 960;

export function sortBrandLeaderboardRows(
  rows: BrandLeaderboardRow[],
  column: BrandLeaderboardSortColumn,
  dir: "asc" | "desc",
): BrandLeaderboardRow[] {
  const col = BRAND_LEADERBOARD_COLUMNS.find((c) => c.id === column)!;
  const sign = dir === "asc" ? 1 : -1;
  const effectiveSign = col.higherIsBetter ? sign : -sign;

  const valueOf = (row: BrandLeaderboardRow): number | null => {
    switch (column) {
      case "visibility":
        return row.visibilityNum;
      case "shareVoice":
        return row.shareVoiceNum;
      case "mention":
        return row.mentionNum;
      case "averageRank":
        return row.averageRankNum;
      case "citation":
        return row.citationNum;
      case "sentiment":
        return row.sentimentNum;
    }
  };

  return [...rows].sort((a, b) => {
    const av = valueOf(a);
    const bv = valueOf(b);
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    return (av - bv) * effectiveSign;
  });
}
