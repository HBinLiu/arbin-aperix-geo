import { useQuery } from "@tanstack/react-query";

import { fetchUsagePackCatalog } from "@/api/billing";
import { queryKeys } from "@/lib/queries";

export function useUsagePackCatalog() {
  return useQuery({
    queryKey: queryKeys.usagePackCatalog,
    queryFn: fetchUsagePackCatalog,
    staleTime: 5 * 60_000,
  });
}
