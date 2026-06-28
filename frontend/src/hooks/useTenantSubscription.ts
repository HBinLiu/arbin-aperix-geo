import { useQuery } from "@tanstack/react-query";

import { fetchTenantSubscription } from "@/api/billing";
import { queryKeys } from "@/lib/queries";

export function useTenantSubscription() {
  return useQuery({
    queryKey: queryKeys.tenantSubscription,
    queryFn: fetchTenantSubscription,
    staleTime: 60_000,
    retry: false,
  });
}
