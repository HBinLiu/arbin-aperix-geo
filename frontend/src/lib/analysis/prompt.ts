import {
  formatDelta,
  formatRank,
  formatRate,
  formatScoreDelta,
  formatSentimentDelta,
  formatSentimentScore,
} from "@/lib/analysis/format";
import type { PromptPerformance, TopicPerformance } from "@/types";

export type TopicPerformanceRow = {
  id: string;
  topicName: string;
  visibility: string;
  visibilityDelta: string | null;
  sentiment: string;
  sentimentDelta: string | null;
  averageRank: string;
  averageRankDelta: string | null;
  citationRate: string;
};

export type PromptPerformanceRow = {
  id: string;
  promptText: string;
  topicName: string;
  visibility: string;
  visibilityDelta: string | null;
  visibilityNum: number;
  sentiment: string;
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
      topicName: row.topic_name ?? "—",
      visibility: formatRate(row.visibility_rate),
      visibilityDelta: formatDelta(row.visibility_rate, prev?.visibility_rate),
      visibilityNum: row.visibility_rate ?? 0,
      sentiment: formatSentimentScore(row.sentiment_score),
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
