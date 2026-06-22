import { useParams } from "react-router-dom";

import { DiagnosisContentDetailView } from "@/components/diagnosis/DiagnosisContentDetailView";
import { useAnalysisFilter } from "@/hooks/useAnalysisFilter";

type ContentDetailPageProps = {
  subjectId: string;
};

function decodeRoutePromptId(value: string | undefined): string {
  if (!value) return "";
  try {
    return decodeURIComponent(value).trim();
  } catch {
    return value.trim();
  }
}

/** 诊断中心 · 单条提示词详情 */
export function ContentDetailPage({ subjectId }: ContentDetailPageProps) {
  const { promptId: promptIdParam } = useParams<{ promptId: string }>();
  const promptId = decodeRoutePromptId(promptIdParam);
  const { platforms: platformsMeta } = useAnalysisFilter();

  return (
    <DiagnosisContentDetailView
      subjectId={subjectId}
      promptId={promptId}
      platformsMeta={platformsMeta}
    />
  );
}
