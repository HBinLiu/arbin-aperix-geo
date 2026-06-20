import type { RankRow } from "@/components/analysis/common/AnalysisRankTable";
import {
  formatDelta,
  formatRank,
  formatRate,
  formatScoreDelta,
  formatSentimentDelta,
  formatSentimentScore,
} from "@/lib/analysis/format";
import { entityRankFlags } from "@/lib/analysis/entities";
import type { TopicPerformanceRow } from "@/lib/analysis/prompt";
import type { VisibilityMetricBundle } from "@/lib/analysis/visibility";
import type {
  AnalysisEntityRef,
  DashboardOverviewData,
  DashboardOverviewMetric,
  DashboardOverviewSentimentMetric,
  DashboardOverviewRankRow,
  DashboardOverviewTopic,
} from "@/types";

export function brandRankSubtitle(rank: number | null | undefined): string | null {
  if (rank == null) return null;
  return `所有品牌第 ${rank} 名`;
}

export function brandRankBadge(rank: number | null | undefined): { text: string; variant: "gray" } | null {
  if (rank == null) return null;
  return { text: `#${rank}`, variant: "gray" };
}

export function dashboardRankRows(
  rows: DashboardOverviewRankRow[] | undefined,
  entities: AnalysisEntityRef[],
  focusEntityId: string | undefined,
): RankRow[] {
  if (!rows?.length) return [];
  return rows.map((row) => {
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

export function buildDashboardVisibilityMetric(
  data: DashboardOverviewData | undefined,
  entities: AnalysisEntityRef[],
  focusEntityId: string | undefined,
): VisibilityMetricBundle {
  if (!data) return { rankRows: [] };
  return {
    series: data.visibility_chart.cur_series,
    previousSeries: data.visibility_chart.pre_series,
    ownValue: data.visibility.current ?? undefined,
    prevOwnValue: data.visibility.previous ?? undefined,
    rankRows: dashboardRankRows(data.visibility_table, entities, focusEntityId),
  };
}

export function buildDashboardTopicRows(
  topics: DashboardOverviewTopic[] | undefined,
): TopicPerformanceRow[] {
  return (topics ?? []).map((topic) => ({
    id: topic.topic_id,
    topicName: topic.topic_name,
    visibility: formatRate(topic.visibility.current),
    visibilityDelta: formatDelta(topic.visibility.current, topic.visibility.previous),
    sentiment: formatSentimentScore(topic.sentiment.current),
    sentimentLabel: topic.sentiment.label ?? null,
    sentimentDelta: formatSentimentDelta(topic.sentiment.current, topic.sentiment.previous),
    averageRank: formatRank(topic.average_rank.current),
    averageRankDelta: formatScoreDelta(topic.average_rank.current, topic.average_rank.previous),
    citationRate: formatRate(topic.citation.current),
  }));
}

export type DashboardOverviewView = {
  visibility: DashboardOverviewMetric;
  citation: DashboardOverviewMetric;
  shareVoice: DashboardOverviewMetric;
  sentiment: DashboardOverviewSentimentMetric;
};

export function dashboardOverviewView(
  data: DashboardOverviewData | undefined,
): DashboardOverviewView {
  return {
    visibility: data?.visibility ?? { current: null, previous: null, rank: null },
    citation: data?.citation ?? { current: null, previous: null, rank: null },
    shareVoice: data?.share_voice ?? { current: null, previous: null, rank: null },
    sentiment: data?.sentiment ?? { current: null, previous: null, rank: null, label: null },
  };
}
