import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchCitationDomains, fetchCitationDomainPrompts, fetchCitationDomainUrls, fetchCitationUrls } from "@/api/analysis";
import type { FetchCitationListOptions } from "@/api/analysis";
import { platformFilterKey, topicFilterKey, toAnalysisQueryFilters } from "@/lib/analysis";
import { queryKeys } from "@/lib/queries";
import type {
  AnalysisFilters,
  CitationDomainPromptSortField,
  CitationDomainSortField,
  CitationUrlSortField,
} from "@/types";

function listOptionsKey(options: FetchCitationListOptions) {
  return {
    page: options.page ?? 1,
    pageSize: options.pageSize ?? 10,
    sortBy: options.sortBy ?? "count",
    order: options.order ?? "desc",
    search: options.search?.trim() ?? "",
  };
}

export function useCitationDomains(
  subjectId: string,
  filters: AnalysisFilters,
  options: FetchCitationListOptions & { enabled?: boolean },
) {
  const { enabled = true, ...requestOptions } = options;
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to, entityId, platformIds, topicIds } = queryFilters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);
  const { page, pageSize, sortBy, order, search } = listOptionsKey(requestOptions);

  const query = useQuery({
    queryKey: queryKeys.citationDomains(
      subjectId,
      entityId,
      platformKey,
      topicKey,
      from,
      to,
      page,
      pageSize,
      sortBy,
      order,
      search,
    ),
    queryFn: () =>
      fetchCitationDomains(subjectId, queryFilters, {
        page,
        pageSize,
        sortBy: sortBy as CitationDomainSortField,
        order,
        search: search || undefined,
      }),
    enabled,
  });

  return {
    isLoading: query.isLoading,
    rows: query.data?.items ?? [],
    total: query.data?.total ?? 0,
    page: query.data?.page ?? page,
    pageSize: query.data?.page_size ?? pageSize,
  };
}

export function useCitationUrls(
  subjectId: string,
  filters: AnalysisFilters,
  options: FetchCitationListOptions & { enabled?: boolean },
) {
  const { enabled = true, ...requestOptions } = options;
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to, entityId, platformIds, topicIds } = queryFilters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);
  const { page, pageSize, sortBy, order, search } = listOptionsKey(requestOptions);

  const query = useQuery({
    queryKey: queryKeys.citationUrls(
      subjectId,
      entityId,
      platformKey,
      topicKey,
      from,
      to,
      page,
      pageSize,
      sortBy,
      order,
      search,
    ),
    queryFn: () =>
      fetchCitationUrls(subjectId, queryFilters, {
        page,
        pageSize,
        sortBy: sortBy as CitationUrlSortField,
        order,
        search: search || undefined,
      }),
    enabled,
  });

  return {
    isLoading: query.isLoading,
    rows: query.data?.items ?? [],
    total: query.data?.total ?? 0,
    page: query.data?.page ?? page,
    pageSize: query.data?.page_size ?? pageSize,
  };
}

type CitationDomainListOptions = FetchCitationListOptions & {
  host: string;
  enabled?: boolean;
};

export function useCitationDomainUrls(
  subjectId: string,
  filters: AnalysisFilters,
  options: CitationDomainListOptions,
) {
  const { enabled = true, host, ...requestOptions } = options;
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to, entityId, platformIds, topicIds } = queryFilters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);
  const { page, pageSize, sortBy, order } = listOptionsKey(requestOptions);

  const query = useQuery({
    queryKey: queryKeys.citationDomainUrls(
      subjectId,
      entityId,
      platformKey,
      topicKey,
      host,
      from,
      to,
      page,
      pageSize,
      sortBy,
      order,
    ),
    queryFn: () =>
      fetchCitationDomainUrls(subjectId, queryFilters, {
        host,
        page,
        pageSize,
        sortBy: sortBy as CitationUrlSortField,
        order,
      }),
    enabled: enabled && Boolean(host),
  });

  return {
    isLoading: query.isLoading,
    rows: query.data?.items ?? [],
    total: query.data?.total ?? 0,
    page: query.data?.page ?? page,
    pageSize: query.data?.page_size ?? pageSize,
  };
}

export function useCitationDomainPrompts(
  subjectId: string,
  filters: AnalysisFilters,
  options: CitationDomainListOptions,
) {
  const { enabled = true, host, ...requestOptions } = options;
  const queryFilters = useMemo(() => toAnalysisQueryFilters(filters), [filters]);
  const { from, to, entityId, platformIds, topicIds } = queryFilters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);
  const { page, pageSize, sortBy, order } = listOptionsKey(requestOptions);

  const query = useQuery({
    queryKey: queryKeys.citationDomainPrompts(
      subjectId,
      entityId,
      platformKey,
      topicKey,
      host,
      from,
      to,
      page,
      pageSize,
      sortBy,
      order,
    ),
    queryFn: () =>
      fetchCitationDomainPrompts(subjectId, queryFilters, {
        host,
        page,
        pageSize,
        sortBy: sortBy as CitationDomainPromptSortField,
        order,
      }),
    enabled: enabled && Boolean(host),
  });

  return {
    isLoading: query.isLoading,
    rows: query.data?.items ?? [],
    total: query.data?.total ?? 0,
    page: query.data?.page ?? page,
    pageSize: query.data?.page_size ?? pageSize,
  };
}
