import { useQuery } from "@tanstack/react-query";

import {
  fetchBacklinkOpportunityDetail,
  fetchBacklinkOpportunityPrompts,
  fetchBacklinkOpportunityUrls,
} from "@/api/analysis";
import { platformFilterKey, topicFilterKey } from "@/lib/analysis";
import { paginatedListResult, usePaginatedQuery } from "@/hooks/usePaginatedQuery";
import { queryKeys } from "@/lib/queries";
import type {
  AnalysisFilters,
  CitationDomainPromptSortField,
  CitationUrlSortField,
} from "@/types";

export function useBacklinkOpportunityDetail(
  subjectId: string,
  filters: AnalysisFilters,
  options: { domain: string; enabled?: boolean },
) {
  const { from, to, platformIds, topicIds } = filters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);

  return useQuery({
    queryKey: queryKeys.backlinkOpportunityDetail(
      subjectId,
      platformKey,
      topicKey,
      from,
      to,
      options.domain,
    ),
    queryFn: () =>
      fetchBacklinkOpportunityDetail(subjectId, filters, {
        domain: options.domain,
      }),
    enabled: (options.enabled ?? true) && !!options.domain,
  });
}

export function useBacklinkOpportunityUrls(
  subjectId: string,
  filters: AnalysisFilters,
  options: {
    domain: string;
    page: number;
    pageSize: number;
    sortBy?: CitationUrlSortField;
    order?: "asc" | "desc";
    enabled?: boolean;
  },
) {
  const { from, to, platformIds, topicIds } = filters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);
  const sortBy = options.sortBy ?? "count";
  const order = options.order ?? "desc";

  const query = usePaginatedQuery({
    queryKey: queryKeys.backlinkOpportunityUrls(
      subjectId,
      platformKey,
      topicKey,
      from,
      to,
      options.domain,
      options.page,
      options.pageSize,
      sortBy,
      order,
    ),
    queryFn: () =>
      fetchBacklinkOpportunityUrls(subjectId, filters, {
        domain: options.domain,
        page: options.page,
        pageSize: options.pageSize,
        sortBy,
        order,
      }),
    enabled: (options.enabled ?? true) && !!options.domain,
  });

  return paginatedListResult(query, { page: options.page, pageSize: options.pageSize });
}

export function useBacklinkOpportunityPrompts(
  subjectId: string,
  filters: AnalysisFilters,
  options: {
    domain: string;
    page: number;
    pageSize: number;
    sortBy?: CitationDomainPromptSortField;
    order?: "asc" | "desc";
    enabled?: boolean;
  },
) {
  const { from, to, platformIds, topicIds } = filters;
  const topicKey = topicFilterKey(topicIds);
  const platformKey = platformFilterKey(platformIds);
  const sortBy = options.sortBy ?? "count";
  const order = options.order ?? "desc";

  const query = usePaginatedQuery({
    queryKey: queryKeys.backlinkOpportunityPrompts(
      subjectId,
      platformKey,
      topicKey,
      from,
      to,
      options.domain,
      options.page,
      options.pageSize,
      sortBy,
      order,
    ),
    queryFn: () =>
      fetchBacklinkOpportunityPrompts(subjectId, filters, {
        domain: options.domain,
        page: options.page,
        pageSize: options.pageSize,
        sortBy,
        order,
      }),
    enabled: (options.enabled ?? true) && !!options.domain,
  });

  return paginatedListResult(query, { page: options.page, pageSize: options.pageSize });
}
