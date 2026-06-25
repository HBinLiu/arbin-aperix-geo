import { api } from "@/api/client";
import { buildAnalysisParams } from "@/lib/analysis/filters";
import type { AnalysisEntitiesData, AnalysisQueryFilters, PlatformMatrixRowDimension } from "@/types";
import type {
  BacklinkOpportunityData,
  BacklinkOpportunityDetailData,
  BacklinkOpportunitySortField,
  BacklinkOpportunityUrlRow,
  ContentOpportunityDetailData,
  ContentOpportunitySortField,
  DiagnosisContentListData,
  DiagnosisContentSummaryData,
  CitationAnalysisData,
  CitationDomainAnalysisData,
  CitationDomainBreakdownRow,
  CitationDomainPromptSortField,
  CitationDomainRow,
  CitationDomainSortField,
  CitationListPage,
  CitationUrlRow,
  CitationUrlSortField,
  DashboardOverviewData,
  PlatformAnalysisData,
  PromptPerformancePage,
  PromptPerformanceSortField,
  PromptDetailData,
  RankData,
  SentimentAnalysisData,
  AnalysisResponsesPage,
  AnalysisResponseSortField,
  SentimentTab,
  TopicPerformance,
  VisibilityAnalysisData,
} from "@/types";
import { normalizePlatformMatrixCells } from "@/lib/analysis/platform";

export async function fetchAnalysisEntities(subjectId: string): Promise<AnalysisEntitiesData> {
  const { data } = await api.get<AnalysisEntitiesData>(`/subjects/${subjectId}/entities`);
  return data;
}

export async function fetchOverview(
  subjectId: string,
  filters: AnalysisQueryFilters,
): Promise<DashboardOverviewData> {
  const params = buildAnalysisParams(filters);
  const body: Record<string, string | string[]> = { ...params };
  if (typeof body.platform === "string") {
    body.platform = [body.platform];
  }
  const { data } = await api.post<DashboardOverviewData>(`/subjects/${subjectId}/overview`, body);
  return data;
}

export async function fetchRank(subjectId: string, filters: AnalysisQueryFilters): Promise<RankData> {
  const params = buildAnalysisParams(filters);
  const body: Record<string, string | string[]> = { ...params };
  if (typeof body.platform === "string") {
    body.platform = [body.platform];
  }
  const { data } = await api.post<RankData>(`/subjects/${subjectId}/rank`, body);
  return data;
}

export async function fetchTopicsPerformance(
  subjectId: string,
  filters: AnalysisQueryFilters,
): Promise<TopicPerformance[]> {
  const params = buildAnalysisParams(filters);
  const body: Record<string, string | string[]> = { ...params };
  if (typeof body.platform === "string") {
    body.platform = [body.platform];
  }
  const { data } = await api.post<TopicPerformance[]>(
    `/subjects/${subjectId}/analysis/topics`,
    body,
  );
  return data;
}

export type FetchPromptsPerformanceOptions = {
  page?: number;
  pageSize?: number;
  search?: string;
  topicId?: string | null;
  sortBy?: PromptPerformanceSortField | null;
  order?: "asc" | "desc";
};

export async function fetchPromptsPerformance(
  subjectId: string,
  filters: AnalysisQueryFilters,
  options: FetchPromptsPerformanceOptions = {},
): Promise<PromptPerformancePage> {
  const params = buildAnalysisParams(filters);
  const body: Record<string, string | number | string[] | undefined> = { ...params };
  if (typeof body.platform === "string") {
    body.platform = [body.platform];
  }
  if (options.topicId) {
    body.topic_id = [options.topicId];
  }
  body.page = options.page ?? 1;
  body.page_size = options.pageSize ?? 10;
  const search = options.search?.trim();
  if (search) {
    body.search = search;
  }
  if (options.sortBy) {
    body.sort_by = options.sortBy;
    body.order = options.order ?? "desc";
  }
  const { data } = await api.post<PromptPerformancePage>(
    `/subjects/${subjectId}/analysis/prompts`,
    body,
  );
  return data;
}

export async function fetchPlatformAnalysis(
  subjectId: string,
  filters: AnalysisQueryFilters,
  matrixRow: PlatformMatrixRowDimension,
): Promise<PlatformAnalysisData> {
  const params = buildAnalysisParams(filters);
  const body: Record<string, string | string[]> = { ...params, matrix_row: matrixRow };
  if (typeof body.platform === "string") {
    body.platform = [body.platform];
  }
  const { data } = await api.post<PlatformAnalysisData>(
    `/subjects/${subjectId}/analysis/platform`,
    body,
  );
  return {
    ...data,
    matrix_cells: normalizePlatformMatrixCells(data.matrix_cells),
  };
}

export async function fetchVisibilityAnalysis(
  subjectId: string,
  filters: AnalysisQueryFilters,
  promptId?: string | null,
): Promise<VisibilityAnalysisData> {
  const params = buildAnalysisParams(filters, promptId);
  const body: Record<string, string | string[]> = { ...params };
  if (typeof body.platform === "string") {
    body.platform = [body.platform];
  }
  const { data } = await api.post<VisibilityAnalysisData>(
    `/subjects/${subjectId}/analysis/visibility`,
    body,
  );
  return data;
}

export type FetchCitationListOptions = {
  page?: number;
  pageSize?: number;
  sortBy?: CitationDomainSortField | CitationUrlSortField;
  order?: "asc" | "desc";
  search?: string;
};

export async function fetchCitationAnalysis(
  subjectId: string,
  filters: AnalysisQueryFilters,
  promptId?: string | null,
): Promise<CitationAnalysisData> {
  const params = buildAnalysisParams(filters, promptId);
  const body: Record<string, string | string[]> = { ...params };
  if (typeof body.platform === "string") {
    body.platform = [body.platform];
  }
  const { data } = await api.post<CitationAnalysisData>(
    `/subjects/${subjectId}/analysis/citation`,
    body,
  );
  return data;
}

export async function fetchCitationDomains(
  subjectId: string,
  filters: AnalysisQueryFilters,
  options: FetchCitationListOptions = {},
): Promise<CitationListPage<CitationDomainRow>> {
  const body: Record<string, string | number | string[] | undefined> = {
    ...buildAnalysisParams(filters),
    page: options.page ?? 1,
    page_size: options.pageSize ?? 10,
    sort_by: options.sortBy ?? "count",
    order: options.order ?? "desc",
  };
  if (typeof body.platform === "string") {
    body.platform = [body.platform];
  }
  const search = options.search?.trim();
  if (search) {
    body.search = search;
  }
  const { data } = await api.post<CitationListPage<CitationDomainRow>>(
    `/subjects/${subjectId}/analysis/citation/domains`,
    body,
  );
  return data;
}

export async function fetchCitationUrls(
  subjectId: string,
  filters: AnalysisQueryFilters,
  options: FetchCitationListOptions = {},
): Promise<CitationListPage<CitationUrlRow>> {
  const body: Record<string, string | number | string[] | undefined> = {
    ...buildAnalysisParams(filters),
    page: options.page ?? 1,
    page_size: options.pageSize ?? 10,
    sort_by: options.sortBy ?? "count",
    order: options.order ?? "desc",
  };
  if (typeof body.platform === "string") {
    body.platform = [body.platform];
  }
  const search = options.search?.trim();
  if (search) {
    body.search = search;
  }
  const { data } = await api.post<CitationListPage<CitationUrlRow>>(
    `/subjects/${subjectId}/analysis/citation/urls`,
    body,
  );
  return data;
}

export async function fetchCitationDomainAnalysis(
  subjectId: string,
  filters: AnalysisQueryFilters,
  domain: string,
): Promise<CitationDomainAnalysisData> {
  const body: Record<string, string | string[]> = {
    ...buildAnalysisParams(filters),
    domain,
  };
  if (typeof body.platform === "string") {
    body.platform = [body.platform];
  }
  const { data } = await api.post<CitationDomainAnalysisData>(
    `/subjects/${subjectId}/analysis/citation/domain`,
    body,
  );
  return data;
}

type FetchCitationDomainListOptions = FetchCitationListOptions & {
  domain: string;
};

export async function fetchCitationDomainUrls(
  subjectId: string,
  filters: AnalysisQueryFilters,
  options: FetchCitationDomainListOptions,
): Promise<CitationListPage<CitationUrlRow>> {
  const body: Record<string, string | number | string[] | undefined> = {
    ...buildAnalysisParams(filters),
    domain: options.domain,
    page: options.page ?? 1,
    page_size: options.pageSize ?? 10,
    sort_by: options.sortBy ?? "count",
    order: options.order ?? "desc",
  };
  if (typeof body.platform === "string") {
    body.platform = [body.platform];
  }
  const { data } = await api.post<CitationListPage<CitationUrlRow>>(
    `/subjects/${subjectId}/analysis/citation/domain/urls`,
    body,
  );
  return data;
}

export async function fetchCitationDomainPrompts(
  subjectId: string,
  filters: AnalysisQueryFilters,
  options: FetchCitationDomainListOptions,
): Promise<CitationListPage<CitationDomainBreakdownRow>> {
  const body: Record<string, string | number | string[] | undefined> = {
    ...buildAnalysisParams(filters),
    domain: options.domain,
    page: options.page ?? 1,
    page_size: options.pageSize ?? 10,
    sort_by: options.sortBy ?? "count",
    order: options.order ?? "desc",
  };
  if (typeof body.platform === "string") {
    body.platform = [body.platform];
  }
  const { data } = await api.post<CitationListPage<CitationDomainBreakdownRow>>(
    `/subjects/${subjectId}/analysis/citation/domain/prompts`,
    body,
  );
  return data;
}

export async function fetchSentimentAnalysis(
  subjectId: string,
  filters: AnalysisQueryFilters,
): Promise<SentimentAnalysisData> {
  const params = buildAnalysisParams(filters);
  const body: Record<string, string | string[]> = { ...params };
  if (typeof body.platform === "string") {
    body.platform = [body.platform];
  }
  const { data } = await api.post<SentimentAnalysisData>(
    `/subjects/${subjectId}/analysis/sentiment`,
    body,
  );
  return data;
}

export type FetchAnalysisResponsesOptions = {
  sentimentLabel?: SentimentTab;
  promptId?: string;
  page?: number;
  pageSize?: number;
  sortBy?: AnalysisResponseSortField | null;
  order?: "asc" | "desc";
};

export async function fetchAnalysisResponses(
  subjectId: string,
  filters: AnalysisQueryFilters,
  options: FetchAnalysisResponsesOptions = {},
): Promise<AnalysisResponsesPage> {
  const params = buildAnalysisParams(filters, options.promptId);
  const body: Record<string, string | number | string[] | undefined> = { ...params };
  if (typeof body.platform === "string") {
    body.platform = [body.platform];
  }
  if (options.sentimentLabel) {
    body.sentiment_label = options.sentimentLabel;
  } else {
    delete body.sentiment_label;
  }
  body.page = options.page ?? 1;
  body.page_size = options.pageSize ?? 10;
  if (options.sortBy) {
    body.sort_by = options.sortBy;
    body.order = options.order ?? "desc";
  } else {
    delete body.sort_by;
    body.order = options.order ?? "desc";
  }
  const { data } = await api.post<AnalysisResponsesPage>(
    `/subjects/${subjectId}/analysis/responses`,
    body,
  );
  return data;
}

export async function fetchPromptDetail(
  subjectId: string,
  filters: AnalysisQueryFilters,
  promptId?: string | null,
): Promise<PromptDetailData> {
  const params = buildAnalysisParams(filters, promptId);
  const body: Record<string, string | string[]> = { ...params };
  if (typeof body.platform === "string") {
    body.platform = [body.platform];
  }
  const { data } = await api.post<PromptDetailData>(
    `/subjects/${subjectId}/analysis/prompt/detail`,
    body,
  );
  return data;
}

export async function fetchDiagnosisContentSummary(
  subjectId: string,
  filters: AnalysisQueryFilters,
): Promise<DiagnosisContentSummaryData> {
  const params = buildAnalysisParams(filters);
  const body: Record<string, string | string[]> = { ...params };
  if (typeof body.platform === "string") {
    body.platform = [body.platform];
  }
  const { data } = await api.post<DiagnosisContentSummaryData>(
    `/subjects/${subjectId}/diagnosis/summary`,
    body,
  );
  return data;
}

export async function fetchDiagnosisContent(
  subjectId: string,
  filters: AnalysisQueryFilters,
  options: {
    page?: number;
    pageSize?: number;
    sortBy?: ContentOpportunitySortField | null;
    order?: "asc" | "desc";
  } = {},
): Promise<DiagnosisContentListData> {
  const params = buildAnalysisParams(filters);
  const body: Record<string, string | number | string[] | undefined> = { ...params };
  if (typeof body.platform === "string") {
    body.platform = [body.platform];
  }
  body.page = options.page ?? 1;
  body.page_size = options.pageSize ?? 10;
  if (options.sortBy) {
    body.sort_by = options.sortBy;
    body.order = options.order ?? "asc";
  }
  const { data } = await api.post<DiagnosisContentListData>(
    `/subjects/${subjectId}/diagnosis`,
    body,
  );
  return data;
}

export async function fetchDiagnosisContentDetail(
  subjectId: string,
  filters: AnalysisQueryFilters,
  options: {
    promptId: string;
  },
): Promise<ContentOpportunityDetailData> {
  const params = buildAnalysisParams(filters);
  const body: Record<string, string | string[]> = {
    ...params,
    prompt_id: options.promptId,
  };
  if (typeof body.platform === "string") {
    body.platform = [body.platform];
  }
  const { data } = await api.post<ContentOpportunityDetailData>(
    `/subjects/${subjectId}/diagnosis/detail`,
    body,
  );
  return data;
}

export async function fetchBacklinkOpportunities(
  subjectId: string,
  filters: AnalysisQueryFilters,
  options: {
    page?: number;
    pageSize?: number;
    search?: string;
    sortBy?: BacklinkOpportunitySortField | null;
    order?: "asc" | "desc";
  } = {},
): Promise<BacklinkOpportunityData> {
  const params = buildAnalysisParams(filters);
  const body: Record<string, string | number | string[] | undefined> = { ...params };
  if (typeof body.platform === "string") {
    body.platform = [body.platform];
  }
  body.page = options.page ?? 1;
  body.page_size = options.pageSize ?? 10;
  const search = options.search?.trim();
  if (search) {
    body.search = search;
  }
  if (options.sortBy) {
    body.sort_by = options.sortBy;
    body.order = options.order ?? "asc";
  }
  const { data } = await api.post<BacklinkOpportunityData>(
    `/subjects/${subjectId}/opportunity/backlink`,
    body,
  );
  return data;
}

function buildBacklinkDetailBody(
  filters: AnalysisQueryFilters,
  domain: string,
  extra: Record<string, string | number | string[] | undefined> = {},
) {
  const params = buildAnalysisParams(filters);
  const body: Record<string, string | number | string[] | undefined> = {
    ...params,
    domain,
    ...extra,
  };
  if (typeof body.platform === "string") {
    body.platform = [body.platform];
  }
  return body;
}

export async function fetchBacklinkOpportunityDetail(
  subjectId: string,
  filters: AnalysisQueryFilters,
  options: { domain: string },
): Promise<BacklinkOpportunityDetailData> {
  const { data } = await api.post<BacklinkOpportunityDetailData>(
    `/subjects/${subjectId}/opportunity/backlink/detail`,
    buildBacklinkDetailBody(filters, options.domain),
  );
  return data;
}

export async function fetchBacklinkOpportunityUrls(
  subjectId: string,
  filters: AnalysisQueryFilters,
  options: {
    domain: string;
    page?: number;
    pageSize?: number;
    sortBy?: CitationUrlSortField;
    order?: "asc" | "desc";
  },
) {
  const { data } = await api.post<{
    items: BacklinkOpportunityUrlRow[];
    total: number;
    page: number;
    page_size: number;
    response_total: number;
  }>(
    `/subjects/${subjectId}/opportunity/backlink/detail/urls`,
    buildBacklinkDetailBody(filters, options.domain, {
      page: options.page ?? 1,
      page_size: options.pageSize ?? 15,
      sort_by: options.sortBy ?? "count",
      order: options.order ?? "desc",
    }),
  );
  return data;
}

export async function fetchBacklinkOpportunityPrompts(
  subjectId: string,
  filters: AnalysisQueryFilters,
  options: {
    domain: string;
    page?: number;
    pageSize?: number;
    sortBy?: CitationDomainPromptSortField;
    order?: "asc" | "desc";
  },
) {
  const { data } = await api.post<{
    items: CitationDomainBreakdownRow[];
    total: number;
    page: number;
    page_size: number;
    response_total: number;
  }>(
    `/subjects/${subjectId}/opportunity/backlink/detail/prompts`,
    buildBacklinkDetailBody(filters, options.domain, {
      page: options.page ?? 1,
      page_size: options.pageSize ?? 15,
      sort_by: options.sortBy ?? "count",
      order: options.order ?? "desc",
    }),
  );
  return data;
}
