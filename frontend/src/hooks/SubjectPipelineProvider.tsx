import type { ReactNode } from "react";

import {
  SubjectPipelineContext,
  useSubjectPipelineState,
} from "@/hooks/useSubjectPipeline";

type SubjectPipelineProviderProps = {
  subjectId: string;
  children: ReactNode;
};

/** 控制台内单例 pipeline 状态（SSE），避免多组件重复请求 REST。 */
export function SubjectPipelineProvider({ subjectId, children }: SubjectPipelineProviderProps) {
  const value = useSubjectPipelineState(subjectId);
  return (
    <SubjectPipelineContext.Provider value={value}>{children}</SubjectPipelineContext.Provider>
  );
}
