import { useQuery } from "@tanstack/react-query";

import { fetchSubjectKnowledge } from "@/api/knowledge";
import { knowledgeNeedsReindex } from "@/lib/knowledge/display";
import { queryKeys, sessionCatalogQueryOptions } from "@/lib/queries";

const INDEX_POLL_MS = 3000;

export function useSubjectKnowledge(subjectId: string) {
  return useQuery({
    queryKey: queryKeys.subjectKnowledge(subjectId),
    queryFn: () => fetchSubjectKnowledge(subjectId),
    ...sessionCatalogQueryOptions,
    refetchInterval: (query) => {
      const knowledge = query.state.data?.knowledge;
      if (!knowledge) return false;
      const indexStatus = knowledge.index_status;
      const extractStatus = knowledge.extract_status;
      const indexing = indexStatus === "indexing" || indexStatus === "pending";
      const extracting = extractStatus === "pending";
      const waitingReindex = knowledgeNeedsReindex(knowledge);
      return indexing || extracting || waitingReindex ? INDEX_POLL_MS : false;
    },
  });
}
