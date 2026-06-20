import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  fetchBacklinkOpportunityDetail,
  fetchBacklinkOpportunityPrompts,
  fetchBacklinkOpportunityUrls,
} from "@/api/analysis";
import { platformFilterKey, topicFilterKey } from "@/lib/analysis";
import { queryKeys } from "@/lib/queries";
import type {
  AnalysisFilters,
  CitationDomainPromptSortField,
  CitationUrlSortField,
} from "@/types";

export function useBacklinkOpportunityDetail(
  subjectId: string,
  filters: AnalysisFilters,
  options: { host: string; enabled?: boolean },
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
      options.host,
    ),
    queryFn: () =>
      fetchBacklinkOpportunityDetail(subjectId, filters, {
        host: options.host,
      }),
    enabled: (options.enabled ?? true) && !!options.host,
  });
}

export function useBacklinkOpportunityUrls(
  subjectId: string,
  filters: AnalysisFilters,
  options: {
    host: string;
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

  const query = useQuery({
    queryKey: queryKeys.backlinkOpportunityUrls(
      subjectId,
      platformKey,
      topicKey,
      from,
      to,
      options.host,
      options.page,
      options.pageSize,
      sortBy,
      order,
    ),
    queryFn: () =>
      fetchBacklinkOpportunityUrls(subjectId, filters, {
        host: options.host,
        page: options.page,
        pageSize: options.pageSize,
        sortBy,
        order,
      }),
    enabled: (options.enabled ?? true) && !!options.host,
  });

  return useMemo(
    () => ({
      ...query,
      rows: query.data?.items ?? [],
      total: query.data?.total ?? 0,
    }),
    [query],
  );
}

export function useBacklinkOpportunityPrompts(
  subjectId: string,
  filters: AnalysisFilters,
  options: {
    host: string;
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

  const query = useQuery({
    queryKey: queryKeys.backlinkOpportunityPrompts(
      subjectId,
      platformKey,
      topicKey,
      from,
      to,
      options.host,
      options.page,
      options.pageSize,
      sortBy,
      order,
    ),
    queryFn: () =>
      fetchBacklinkOpportunityPrompts(subjectId, filters, {
        host: options.host,
        page: options.page,
        pageSize: options.pageSize,
        sortBy,
        order,
      }),
    enabled: (options.enabled ?? true) && !!options.host,
  });

  return useMemo(
    () => ({
      ...query,
      rows: query.data?.items ?? [],
      total: query.data?.total ?? 0,
    }),
    [query],
  );
}
