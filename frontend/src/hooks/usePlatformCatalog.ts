import { useAnalysisFilter } from "@/hooks/useAnalysisFilter";

/** 全量平台目录，与 FilterBar / GET /sampling/platforms 同源。 */
export function usePlatformCatalog() {
  return useAnalysisFilter().platformCatalog;
}
