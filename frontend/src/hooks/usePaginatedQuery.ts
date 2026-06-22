import {
  keepPreviousData,
  useQuery,
  type DefaultError,
  type QueryKey,
  type UseQueryOptions,
  type UseQueryResult,
} from "@tanstack/react-query";

export type PaginatedListData<T> = {
  items: T[];
  total: number;
  page?: number;
  page_size?: number;
};

type PaginatedQueryOptions<
  TQueryFnData,
  TError,
  TData,
  TQueryKey extends QueryKey,
> = Omit<UseQueryOptions<TQueryFnData, TError, TData, TQueryKey>, "placeholderData">;

export type PaginatedQueryResult<TData, TError = DefaultError> = UseQueryResult<TData, TError> & {
  /** 首次加载（无数据）→ 骨架屏 */
  loading: boolean;
  /** 翻页/排序（有 placeholder 数据）→ 表格遮罩 */
  fetching: boolean;
};

/** 分页列表 query：keepPreviousData + 继承全局 staleTime（30s），附带 loading/fetching 状态 */
export function usePaginatedQuery<
  TQueryFnData,
  TError = DefaultError,
  TData = TQueryFnData,
  TQueryKey extends QueryKey = QueryKey,
>(
  options: PaginatedQueryOptions<TQueryFnData, TError, TData, TQueryKey>,
): PaginatedQueryResult<TData, TError> {
  const query = useQuery({
    ...options,
    placeholderData: keepPreviousData,
  });

  return {
    ...query,
    loading: query.isPending,
    fetching: query.isFetching && !query.isPending,
  };
}

export function paginatedListResult<TItem>(
  query: PaginatedQueryResult<PaginatedListData<TItem>>,
  fallback: { page: number; pageSize: number },
) {
  return {
    loading: query.loading,
    fetching: query.fetching,
    rows: query.data?.items ?? [],
    total: query.data?.total ?? 0,
    page: query.data?.page ?? fallback.page,
    pageSize: query.data?.page_size ?? fallback.pageSize,
  };
}
