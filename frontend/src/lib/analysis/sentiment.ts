import type { RankRow } from "@/components/analysis/common/AnalysisRankTable";
import { formatSentimentDelta, formatSentimentScore } from "@/lib/analysis/format";
import { entityRankFlags } from "@/lib/analysis/entities";
import type {
  AnalysisEntityRef,
  SentimentAnalysisData,
  SentimentTab,
} from "@/types";

export const SENTIMENT_SECTION_HEIGHT = 380;
export const SENTIMENT_RANK_TABLE_HEIGHT = SENTIMENT_SECTION_HEIGHT - 24;

export const SENTIMENT_BAR_COLORS: Record<SentimentTab, string> = {
  positive: "#22c55e",
  neutral: "#f97316",
  negative: "#ef4444",
};

export const SENTIMENT_TABS: { id: SentimentTab; label: string }[] = [
  { id: "positive", label: "正面" },
  { id: "neutral", label: "中立" },
  { id: "negative", label: "负面" },
];

export const SENTIMENT_LABELS: Record<SentimentTab, string> = {
  positive: "正面",
  neutral: "中立",
  negative: "负面",
};

export function sentimentLabelFromTab(sentiment: string): string {
  return SENTIMENT_LABELS[sentiment as SentimentTab] ?? sentiment;
}

/** 将后端 sentiment_label（positive/neutral/negative）映射为展示文案 */
export function sentimentDisplayLabel(label: string | null | undefined): string {
  if (label == null || label === "") return "-";
  return sentimentLabelFromTab(label);
}

export function buildSentimentRankRows(
  rows: SentimentAnalysisData["rank_table"] | undefined,
  entities: AnalysisEntityRef[],
  focusEntityId: string | undefined,
): RankRow[] {
  return (rows ?? []).map((row) => {
    const { isOwn, isFocus } = entityRankFlags(entities, row.id, focusEntityId);
    return {
      id: row.id,
      label: row.label,
      domain: row.domain || null,
      value: formatSentimentScore(row.cur_value),
      valueNum: row.cur_value ?? undefined,
      delta: formatSentimentDelta(row.cur_value, row.pre_value),
      deltaSortNum:
        row.cur_value != null && row.pre_value != null ? row.cur_value - row.pre_value : null,
      sentimentLabel: row.cur_label ?? null,
      isOwn,
      isFocus,
    };
  });
}

export type SentimentOverviewData = {
  score: number | null | undefined;
  scoreLabel: string;
  distributionSeries: SentimentAnalysisData["distribution_series"];
  rankRows: RankRow[];
};

export function buildSentimentOverview(
  data: SentimentAnalysisData | undefined,
  entities: AnalysisEntityRef[],
  focusEntityId: string | undefined,
): SentimentOverviewData {
  return {
    score: data?.sentiment_score,
    scoreLabel: sentimentDisplayLabel(data?.sentiment_label),
    distributionSeries: data?.distribution_series ?? [],
    rankRows: buildSentimentRankRows(data?.rank_table, entities, focusEntityId),
  };
}

export function formatSentimentDateTime(iso: string): string {
  const date = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}
