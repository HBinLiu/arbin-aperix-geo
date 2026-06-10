import { api } from "@/api/client";
import {
  ANALYSIS_PARAMS_SERIALIZER,
  buildAnalysisParams,
} from "@/lib/analysis/filters";
import type { AnalysisQueryFilters } from "@/types";
import type {
  BacklinkOpportunityData,
  ContentOpportunityData,
  DiagnosisData,
  CitationAnalysisData,
  CitationDomainAnalysisData,
  CitationRankData,
  CitationsData,
  DailySentimentSeries,
  OverviewMetrics,
  PlatformPerformance,
  PlatformMatrixData,
  PromptPerformance,
  PromptDetailData,
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
  filters?: AnalysisQueryFilters,
  promptId?: string | null,
): Promise<PlatformPerformance[]> {
  const { data } = await api.get<PlatformPerformance[]>(
    `/subjects/${subjectId}/platforms-performance`,
    {
      params: buildAnalysisParams(from, to, filters, promptId),
      paramsSerializer: ANALYSIS_PARAMS_SERIALIZER,
    },
  );
  return data;
}

export async function fetchVisibilityAnalysis(
  subjectId: string,
  from: string,
  to: string,
  filters?: AnalysisQueryFilters,
  promptId?: string | null,
): Promise<VisibilityAnalysisData> {
  const { data } = await api.get<VisibilityAnalysisData>(
    `/subjects/${subjectId}/visibility-analysis`,
    {
      params: buildAnalysisParams(from, to, filters, promptId),
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
  promptId?: string | null,
): Promise<CitationAnalysisData> {
  const { data } = await api.get<CitationAnalysisData>(
    `/subjects/${subjectId}/citation-analysis`,
    {
      params: buildAnalysisParams(from, to, filters, promptId),
      paramsSerializer: ANALYSIS_PARAMS_SERIALIZER,
    },
  );
  return data;
}

export async function fetchCitationDomainAnalysis(
  subjectId: string,
  host: string,
  from: string,
  to: string,
  filters?: AnalysisQueryFilters,
): Promise<CitationDomainAnalysisData> {
  const { data } = await api.get<CitationDomainAnalysisData>(
    `/subjects/${subjectId}/citation-domain-analysis`,
    {
      params: { ...buildAnalysisParams(from, to, filters), host },
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

export async function fetchPromptDetail(
  subjectId: string,
  from: string,
  to: string,
  filters?: AnalysisQueryFilters,
  promptId?: string | null,
): Promise<PromptDetailData> {
  const { data } = await api.get<PromptDetailData>(`/subjects/${subjectId}/prompt-detail`, {
    params: buildAnalysisParams(from, to, filters, promptId),
    paramsSerializer: ANALYSIS_PARAMS_SERIALIZER,
  });
  return data;
}

export async function fetchContentOpportunities(
  subjectId: string,
  from: string,
  to: string,
  filters?: AnalysisQueryFilters,
  promptId?: string | null,
): Promise<ContentOpportunityData> {
  const { data } = await api.get<ContentOpportunityData>(
    `/subjects/${subjectId}/content-opportunities`,
    {
      params: buildAnalysisParams(from, to, filters, promptId),
      paramsSerializer: ANALYSIS_PARAMS_SERIALIZER,
    },
  );
  return data;
}

export async function fetchBacklinkOpportunities(
  subjectId: string,
  from: string,
  to: string,
  filters?: AnalysisQueryFilters,
): Promise<BacklinkOpportunityData> {
  const { data } = await api.get<BacklinkOpportunityData>(
    `/subjects/${subjectId}/backlink-opportunities`,
    {
      params: buildAnalysisParams(from, to, filters),
      paramsSerializer: ANALYSIS_PARAMS_SERIALIZER,
    },
  );
  return data;
}

export async function fetchDiagnosis(
  subjectId: string,
  from: string,
  to: string,
  filters?: AnalysisQueryFilters,
): Promise<DiagnosisData> {
  const { data } = await api.get<DiagnosisData>(`/subjects/${subjectId}/diagnosis`, {
    params: buildAnalysisParams(from, to, filters),
    paramsSerializer: ANALYSIS_PARAMS_SERIALIZER,
  });
  return data;
}
