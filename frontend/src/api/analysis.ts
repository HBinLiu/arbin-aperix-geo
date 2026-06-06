import { api } from "@/api/client";
import {
  ANALYSIS_PARAMS_SERIALIZER,
  buildAnalysisParams,
} from "@/lib/analysis/filters";
import type { AnalysisQueryFilters } from "@/types";
import type {
  CitationAnalysisData,
  CitationRankData,
  CitationsData,
  DailySentimentSeries,
  OverviewMetrics,
  PlatformPerformance,
  PlatformMatrixData,
  PromptPerformance,
  RankData,
  SentimentAnalysisData,
  TopicPerformance,
  VisibilityAnalysisData,
} from "@/types";

export async function fetchOverview(
  subjectId: string,
  from: string,
  to: string,
  filters?: AnalysisQueryFilters,
): Promise<OverviewMetrics> {
  const { data } = await api.get<OverviewMetrics>(`/subjects/${subjectId}/overview`, {
    params: buildAnalysisParams(from, to, filters),
    paramsSerializer: ANALYSIS_PARAMS_SERIALIZER,
  });
  return data;
}

export async function fetchRank(
  subjectId: string,
  from: string,
  to: string,
  filters?: AnalysisQueryFilters,
): Promise<RankData> {
  const { data } = await api.get<RankData>(`/subjects/${subjectId}/rank`, {
    params: buildAnalysisParams(from, to, filters),
    paramsSerializer: ANALYSIS_PARAMS_SERIALIZER,
  });
  return data;
}

export async function fetchTopicsPerformance(
  subjectId: string,
  from: string,
  to: string,
  filters?: AnalysisQueryFilters,
): Promise<TopicPerformance[]> {
  const { data } = await api.get<TopicPerformance[]>(`/subjects/${subjectId}/topics-performance`, {
    params: buildAnalysisParams(from, to, filters),
    paramsSerializer: ANALYSIS_PARAMS_SERIALIZER,
  });
  return data;
}

export async function fetchPromptsPerformance(
  subjectId: string,
  from: string,
  to: string,
  filters?: AnalysisQueryFilters,
): Promise<PromptPerformance[]> {
  const { data } = await api.get<PromptPerformance[]>(`/subjects/${subjectId}/prompts-performance`, {
    params: buildAnalysisParams(from, to, filters),
    paramsSerializer: ANALYSIS_PARAMS_SERIALIZER,
  });
  return data;
}

export async function fetchPlatformMatrix(
  subjectId: string,
  from: string,
  to: string,
  filters?: AnalysisQueryFilters,
): Promise<PlatformMatrixData> {
  const { data } = await api.get<PlatformMatrixData>(`/subjects/${subjectId}/platform-matrix`, {
    params: buildAnalysisParams(from, to, filters),
    paramsSerializer: ANALYSIS_PARAMS_SERIALIZER,
  });
  return data;
}

export async function fetchPlatformPerformance(
  subjectId: string,
  from: string,
  to: string,
): Promise<PlatformPerformance[]> {
  const { data } = await api.get<PlatformPerformance[]>(
    `/subjects/${subjectId}/platforms-performance`,
    { params: { from, to } },
  );
  return data;
}

export async function fetchVisibilityAnalysis(
  subjectId: string,
  from: string,
  to: string,
  filters?: AnalysisQueryFilters,
): Promise<VisibilityAnalysisData> {
  const { data } = await api.get<VisibilityAnalysisData>(
    `/subjects/${subjectId}/visibility-analysis`,
    {
      params: buildAnalysisParams(from, to, filters),
      paramsSerializer: ANALYSIS_PARAMS_SERIALIZER,
    },
  );
  return data;
}

export async function fetchCitationAnalysis(
  subjectId: string,
  from: string,
  to: string,
  filters?: AnalysisQueryFilters,
): Promise<CitationAnalysisData> {
  const { data } = await api.get<CitationAnalysisData>(
    `/subjects/${subjectId}/citation-analysis`,
    {
      params: buildAnalysisParams(from, to, filters),
      paramsSerializer: ANALYSIS_PARAMS_SERIALIZER,
    },
  );
  return data;
}

export async function fetchCitationRank(
  subjectId: string,
  from: string,
  to: string,
): Promise<CitationRankData> {
  const { data } = await api.get<CitationRankData>(`/subjects/${subjectId}/citation-rank`, {
    params: { from, to },
  });
  return data;
}

export async function fetchSentimentAnalysis(
  subjectId: string,
  from: string,
  to: string,
  filters?: AnalysisQueryFilters,
): Promise<SentimentAnalysisData> {
  const { data } = await api.get<SentimentAnalysisData>(
    `/subjects/${subjectId}/sentiment-analysis`,
    {
      params: buildAnalysisParams(from, to, filters),
      paramsSerializer: ANALYSIS_PARAMS_SERIALIZER,
    },
  );
  return data;
}

export async function fetchDailySentiment(
  subjectId: string,
  from: string,
  to: string,
): Promise<DailySentimentSeries> {
  const { data } = await api.get<DailySentimentSeries>(`/subjects/${subjectId}/daily-sentiment`, {
    params: { from, to },
  });
  return data;
}

export async function fetchCitations(
  subjectId: string,
  from: string,
  to: string,
): Promise<CitationsData> {
  const { data } = await api.get<CitationsData>(`/subjects/${subjectId}/citations`, {
    params: { from, to },
  });
  return data;
}
