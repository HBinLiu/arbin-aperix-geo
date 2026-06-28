import { useQuery } from "@tanstack/react-query";

import { fetchPlanCatalog } from "@/api/billing";
import { queryKeys } from "@/lib/queries";

export function usePlanCatalog() {
  return useQuery({
    queryKey: queryKeys.planCatalog,
    queryFn: fetchPlanCatalog,
    staleTime: 5 * 60_000,
  });
}
