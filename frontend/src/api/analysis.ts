import { api } from "@/api/client";
import {
  ANALYSIS_PARAMS_SERIALIZER,
  buildAnalysisParams,
} from "@/lib/analysis/filters";
import type { AnalysisEntitiesData, AnalysisQueryFilters } from "@/types";
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

export async function fetchAnalysisEntities(subjectId: string): Promise<AnalysisEntitiesData> {
  const { data } = await api.get<AnalysisEntitiesData>(`/subjects/${subjectId}/analysis/entities`);
  return data;
}

export async function fetchOverview(
  subjectId: string,
  filters: AnalysisQueryFilters | undefined,
  from: string,
  to: string,
): Promise<OverviewMetrics> {
  const { data } = await api.get<OverviewMetrics>(`/subjects/${subjectId}/overview`, {
    params: buildAnalysisParams(from, to, filters),
    paramsSerializer: ANALYSIS_PARAMS_SERIALIZER,
  });
  return data;
}

export async function fetchRank(
  subjectId: string,
  filters: AnalysisQueryFilters | undefined,
  from: string,
  to: string,
): Promise<RankData> {
  const { data } = await api.get<RankData>(`/subjects/${subjectId}/rank`, {
    params: buildAnalysisParams(from, to, filters),
    paramsSerializer: ANALYSIS_PARAMS_SERIALIZER,
  });
  return data;
}

export async function fetchTopicsPerformance(
  subjectId: string,
  filters: AnalysisQueryFilters | undefined,
  from: string,
  to: string,
): Promise<TopicPerformance[]> {
  const { data } = await api.get<TopicPerformance[]>(`/subjects/${subjectId}/topics-performance`, {
    params: buildAnalysisParams(from, to, filters),
    paramsSerializer: ANALYSIS_PARAMS_SERIALIZER,
  });
  return data;
}

export async function fetchPromptsPerformance(
  subjectId: string,
  filters: AnalysisQueryFilters | undefined,
  from: string,
  to: string,
): Promise<PromptPerformance[]> {
  const { data } = await api.get<PromptPerformance[]>(`/subjects/${subjectId}/prompts-performance`, {
    params: buildAnalysisParams(from, to, filters),
    paramsSerializer: ANALYSIS_PARAMS_SERIALIZER,
  });
  return data;
}

export async function fetchPlatformMatrix(
  subjectId: string,
  filters: AnalysisQueryFilters | undefined,
  from: string,
  to: string,
): Promise<PlatformMatrixData> {
  const { data } = await api.get<PlatformMatrixData>(`/subjects/${subjectId}/platform-matrix`, {
    params: buildAnalysisParams(from, to, filters),
    paramsSerializer: ANALYSIS_PARAMS_SERIALIZER,
  });
  return data;
}

export async function fetchPlatformPerformance(
  subjectId: string,
  filters: AnalysisQueryFilters | undefined,
  from: string,
  to: string,
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
  filters: AnalysisQueryFilters | undefined,
  from: string,
  to: string,
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
  filters: AnalysisQueryFilters | undefined,
  from: string,
  to: string,
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
  filters: AnalysisQueryFilters | undefined,
  host: string,
  from: string,
  to: string,
): Promise<CitationDomainAnalysisData> {
  const { data } = await api.get<CitationDomainAnalysisData>(
    `/subjects/${subjectId}/citation-domain-analysis`,
    {
      params: buildAnalysisParams(from, to, filters, null, host),
      paramsSerializer: ANALYSIS_PARAMS_SERIALIZER,
    },
  );
  return data;
}

export async function fetchCitationRank(
  subjectId: string,
  filters: AnalysisQueryFilters | undefined,
  from: string,
  to: string,
): Promise<CitationRankData> {
  const { data } = await api.get<CitationRankData>(`/subjects/${subjectId}/citation-rank`, {
    params: buildAnalysisParams(from, to, filters),
    paramsSerializer: ANALYSIS_PARAMS_SERIALIZER,
  });
  return data;
}

export async function fetchSentimentAnalysis(
  subjectId: string,
  filters: AnalysisQueryFilters | undefined,
  from: string,
  to: string,
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
  filters: AnalysisQueryFilters | undefined,
  from: string,
  to: string,
): Promise<DailySentimentSeries> {
  const { data } = await api.get<DailySentimentSeries>(`/subjects/${subjectId}/daily-sentiment`, {
    params: buildAnalysisParams(from, to, filters),
    paramsSerializer: ANALYSIS_PARAMS_SERIALIZER,
  });
  return data;
}

export async function fetchCitations(
  subjectId: string,
  filters: AnalysisQueryFilters | undefined,
  from: string,
  to: string,
): Promise<CitationsData> {
  const { data } = await api.get<CitationsData>(`/subjects/${subjectId}/citations`, {
    params: buildAnalysisParams(from, to, filters),
    paramsSerializer: ANALYSIS_PARAMS_SERIALIZER,
  });
  return data;
}

export async function fetchPromptDetail(
  subjectId: string,
  filters: AnalysisQueryFilters | undefined,
  from: string,
  to: string,
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
  filters: AnalysisQueryFilters | undefined,
  from: string,
  to: string,
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
  filters: AnalysisQueryFilters | undefined,
  from: string,
  to: string,
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
  filters: AnalysisQueryFilters | undefined,
  from: string,
  to: string,
): Promise<DiagnosisData> {
  const { data } = await api.get<DiagnosisData>(`/subjects/${subjectId}/diagnosis`, {
    params: buildAnalysisParams(from, to, filters),
    paramsSerializer: ANALYSIS_PARAMS_SERIALIZER,
  });
  return data;
}
