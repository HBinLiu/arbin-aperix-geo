import {
  formatRate,
  formatRankMetric,
  formatSentimentScore,
} from "@/lib/analysis/format";
import type { RankData } from "@/types";

export type RankBoardSortColumn =
  | "visibility"
  | "shareVoice"
  | "mention"
  | "averageRank"
  | "citation"
  | "sentiment";

export type RankBoardRow = {
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

export function buildRankBoardRows(data: RankData): RankBoardRow[] {
  const labels = Object.keys(data.visibility_share).sort(
    (a, b) => (data.visibility_share[b] ?? 0) - (data.visibility_share[a] ?? 0),
  );

  return labels.map((label) => {
    const visibilityNum = data.visibility_share[label] ?? 0;
    const shareVoice = formatShareVoice(data.share_voice[label]);
    const mentionNum = data.mention_rate[label] ?? 0;
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

export const RANK_BOARD_INDEX_COL_WIDTH = "3%";
export const RANK_BOARD_BRAND_COL_WIDTH = "25%";

export const RANK_BOARD_COLUMNS: {
  id: RankBoardSortColumn;
  label: string;
  /** 数值越大越好；平均排名为 false（越小越好） */
  higherIsBetter: boolean;
  width: string;
}[] = [
  {
    id: "visibility",
    label: "可见度",
    higherIsBetter: true,
    width: "12%",
  },
  {
    id: "shareVoice",
    label: "声量份额",
    higherIsBetter: true,
    width: "12%",
  },
  {
    id: "mention",
    label: "AI 提及",
    higherIsBetter: true,
    width: "12%",
  },
  {
    id: "averageRank",
    label: "平均排名",
    higherIsBetter: false,
    width: "12%",
  },
  {
    id: "citation",
    label: "引用率",
    higherIsBetter: true,
    width: "12%",
  },
  {
    id: "sentiment",
    label: "情感倾向分数",
    higherIsBetter: true,
    width: "12%",
  },
];

export const RANK_BOARD_MIN_WIDTH = 960;

export function sortRankBoardRows(
  rows: RankBoardRow[],
  column: RankBoardSortColumn,
  dir: "asc" | "desc",
): RankBoardRow[] {
  const col = RANK_BOARD_COLUMNS.find((c) => c.id === column)!;
  const sign = dir === "asc" ? 1 : -1;
  const effectiveSign = col.higherIsBetter ? sign : -sign;

  const valueOf = (row: RankBoardRow): number | null => {
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
