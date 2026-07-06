import { useQuery } from "@tanstack/react-query";

import { fetchSubjectKnowledge } from "@/api/knowledge";
import { queryKeys, sessionCatalogQueryOptions } from "@/lib/queries";

const INDEX_POLL_MS = 3000;

export function useSubjectKnowledge(subjectId: string) {
  return useQuery({
    queryKey: queryKeys.subjectKnowledge(subjectId),
    queryFn: () => fetchSubjectKnowledge(subjectId),
    ...sessionCatalogQueryOptions,
    refetchInterval: (query) => {
      const indexStatus = query.state.data?.knowledge?.index_status;
      return indexStatus === "indexing" || indexStatus === "pending" ? INDEX_POLL_MS : false;
    },
  });
}
