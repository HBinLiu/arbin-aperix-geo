import { useQuery } from "@tanstack/react-query";

import { fetchTenantSubscription } from "@/api/billing";
import { queryKeys } from "@/lib/queries";

export function useTenantSubscription() {
  return useQuery({
    queryKey: queryKeys.tenantSubscription,
    queryFn: fetchTenantSubscription,
    // Gate / quota UI：比全局默认更短，并在切回窗口时刷新
    staleTime: 15_000,
    refetchOnWindowFocus: true,
    retry: false,
  });
}
