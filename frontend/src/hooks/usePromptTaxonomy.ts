import { useQuery } from "@tanstack/react-query";

import { fetchPromptTaxonomy } from "@/api/prompt";
import { fallbackPromptTaxonomy } from "@/lib/prompt/taxonomy";
import { queryKeys } from "@/lib/queries";

export function usePromptTaxonomy() {
  const query = useQuery({
    queryKey: queryKeys.promptTaxonomy,
    queryFn: fetchPromptTaxonomy,
    staleTime: Infinity,
  });

  return {
    ...query,
    taxonomy: query.data ?? fallbackPromptTaxonomy(),
  };
}
