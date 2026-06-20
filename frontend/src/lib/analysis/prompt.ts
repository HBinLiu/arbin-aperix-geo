import {
  formatDelta,
  formatRank,
  formatRate,
  formatScoreDelta,
  formatSentimentDelta,
  formatSentimentScore,
} from "@/lib/analysis/format";
import type { PromptPerformance, TopicPerformance, PromptPerformanceSortField } from "@/types";

export type PromptTableSortKey = "visibility" | "sentiment" | "averageRank" | "citationRate";

export const PROMPT_SORT_TO_API: Record<PromptTableSortKey, PromptPerformanceSortField> = {
  visibility: "visibility_rate",
  sentiment: "sentiment_score",
  averageRank: "average_rank",
  citationRate: "citation_rate",
};

export function promptSortToApiField(
  key: PromptTableSortKey | null | undefined,
): PromptPerformanceSortField | null {
  if (!key) return null;
  return PROMPT_SORT_TO_API[key];
}

export type TopicPerformanceRow = {
  id: string;
  topicName: string;
  visibility: string;
  visibilityDelta: string | null;
  sentiment: string;
  sentimentLabel: string | null;
  sentimentDelta: string | null;
  averageRank: string;
  averageRankDelta: string | null;
  citationRate: string;
};

export type PromptPerformanceRow = {
  id: string;
  promptText: string;
  topicId: string | null;
  topicName: string;
  funnelStage: string | null;
  searchIntent: string | null;
  visibility: string;
  visibilityDelta: string | null;
  visibilityNum: number;
  sentiment: string;
  sentimentLabel: string | null;
  sentimentDelta: string | null;
  sentimentNum: number | null;
  averageRank: string;
  averageRankDelta: string | null;
  averageRankNum: number | null;
  citationRate: string;
  citationNum: number | null;
};

function indexByTopicId(rows: TopicPerformance[]): Map<string, TopicPerformance> {
  return new Map(rows.map((row) => [row.topic_id, row]));
}

function indexByPromptId(rows: PromptPerformance[]): Map<string, PromptPerformance> {
  return new Map(rows.map((row) => [row.prompt_id, row]));
}

export function buildTopicPerformanceRows(
  current: TopicPerformance[],
  previous: TopicPerformance[],
): TopicPerformanceRow[] {
  const prevMap = indexByTopicId(previous);

  return [...current]
    .sort((a, b) => (b.visibility_rate ?? 0) - (a.visibility_rate ?? 0))
    .map((row) => {
      const prev = prevMap.get(row.topic_id);
      return {
        id: row.topic_id,
        topicName: row.topic_name,
        visibility: formatRate(row.visibility_rate),
        visibilityDelta: formatDelta(row.visibility_rate, prev?.visibility_rate),
        sentiment: formatSentimentScore(row.sentiment_score),
        sentimentLabel: row.sentiment_label ?? null,
        sentimentDelta: formatSentimentDelta(row.sentiment_score, prev?.sentiment_score),
        averageRank: formatRank(row.average_rank),
        averageRankDelta: formatScoreDelta(row.average_rank, prev?.average_rank),
        citationRate: formatRate(row.citation_rate),
      };
    });
}

export function buildPromptPerformanceRows(
  current: PromptPerformance[],
  previous: PromptPerformance[],
): PromptPerformanceRow[] {
  const prevMap = indexByPromptId(previous);

  return current.map((row) => {
    const prev = prevMap.get(row.prompt_id);
    return {
      id: row.prompt_id,
      promptText: row.prompt_text,
      topicId: row.topic_id,
      topicName: row.topic_name ?? "—",
      funnelStage: row.funnel_stage,
      searchIntent: row.search_intent,
      visibility: formatRate(row.visibility_rate),
      visibilityDelta: formatDelta(row.visibility_rate, prev?.visibility_rate),
      visibilityNum: row.visibility_rate ?? 0,
      sentiment: formatSentimentScore(row.sentiment_score),
      sentimentLabel: row.sentiment_label ?? null,
      sentimentDelta: formatSentimentDelta(row.sentiment_score, prev?.sentiment_score),
      sentimentNum: row.sentiment_score,
      averageRank: formatRank(row.average_rank),
      averageRankDelta: formatScoreDelta(row.average_rank, prev?.average_rank),
      averageRankNum: row.average_rank,
      citationRate: formatRate(row.citation_rate),
      citationNum: row.citation_rate,
    };
  });
}
