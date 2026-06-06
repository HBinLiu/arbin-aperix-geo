import type { RankRow } from "@/components/analysis/common/AnalysisRankTable";
import { formatSentimentDelta, formatSentimentScore } from "@/lib/analysis/format";
import { resolvePlatformMeta } from "@/lib/analysis/shared";
import type {
  PlatformPerformance,
  SamplingPlatform,
  SentimentAnalysisData,
  SentimentResponseRow,
  SentimentTab,
} from "@/types";

export const SENTIMENT_SECTION_HEIGHT = 380;
export const SENTIMENT_CHART_HEIGHT = 270;
export const SENTIMENT_RANK_TABLE_HEIGHT = SENTIMENT_SECTION_HEIGHT - 24;

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

export function sentimentLabelFromScore(value: number | null | undefined): string {
  if (value == null) return "-";
  const pct = value * 100;
  if (pct >= 55) return "正面";
  if (pct < 45) return "负面";
  return "中立";
}

export function sentimentLabelFromTab(sentiment: string): string {
  return SENTIMENT_LABELS[sentiment as SentimentTab] ?? sentiment;
}

export function buildSentimentRankRows(
  current: PlatformPerformance[],
  previous: PlatformPerformance[],
  platformsMeta: SamplingPlatform[],
): RankRow[] {
  const prevByPlatform = Object.fromEntries(previous.map((row) => [row.platform, row]));

  return [...current]
    .sort((a, b) => (b.sentiment_score ?? -1) - (a.sentiment_score ?? -1))
    .map((row) => {
      const meta = resolvePlatformMeta(row.platform, platformsMeta);
      const prevScore = prevByPlatform[row.platform]?.sentiment_score;
      return {
        id: row.platform,
        label: meta.label,
        value: formatSentimentScore(row.sentiment_score),
        valueNum: row.sentiment_score ?? undefined,
        delta: formatSentimentDelta(row.sentiment_score, prevScore),
        deltaSortNum:
          row.sentiment_score != null && prevScore != null
            ? row.sentiment_score - prevScore
            : null,
      };
    });
}

export function filterSentimentResponses(
  responses: SentimentResponseRow[],
  tab: SentimentTab,
): SentimentResponseRow[] {
  return responses.filter((row) => row.sentiment === tab);
}

export type SentimentOverviewData = {
  score: number | null | undefined;
  scoreLabel: string;
  distributionSeries: SentimentAnalysisData["distribution_series"];
  rankRows: RankRow[];
  responses: SentimentResponseRow[];
};

export function buildSentimentOverview(
  data: SentimentAnalysisData | undefined,
  platformsMeta: SamplingPlatform[],
): SentimentOverviewData {
  const score = data?.sentiment_score;
  return {
    score,
    scoreLabel: sentimentLabelFromScore(score),
    distributionSeries: data?.distribution_series ?? [],
    rankRows: data
      ? buildSentimentRankRows(
          data.platform_performance,
          data.previous_platform_performance,
          platformsMeta,
        )
      : [],
    responses: data?.responses ?? [],
  };
}

export function formatSentimentDateTime(iso: string): string {
  const date = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}
