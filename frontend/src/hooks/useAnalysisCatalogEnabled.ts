import { useContext } from "react";

import { SubjectPipelineContext } from "@/hooks/useSubjectPipeline";

/** 采样未完成时不拉分析筛选项 catalog（实体/主题/平台）。 */
export function useAnalysisCatalogEnabled(explicit?: boolean): boolean {
  const pipeline = useContext(SubjectPipelineContext);
  if (explicit !== undefined) return explicit;
  if (pipeline == null) return true;
  return pipeline.canShowMetrics;
}
