import { useParams } from "react-router-dom";

import { AnalysisFilterBar } from "@/components/analysis/common/AnalysisFilterBar";
import { OpportunityContentDetailView } from "@/components/opportunity/OpportunityContentDetailView";
import { useAnalysisFilter } from "@/hooks/useAnalysisFilter";
import { useAnalysisFiltersState } from "@/hooks/useAnalysisFiltersState";

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

/** 机会 · 内容 · 单条提示词详情 */
export function ContentDetailPage({ subjectId }: ContentDetailPageProps) {
  const { promptId: promptIdParam } = useParams<{ promptId: string }>();
  const promptId = decodeRoutePromptId(promptIdParam);
  const { platforms: platformsMeta } = useAnalysisFilter();
  const { filters, setFilters } = useAnalysisFiltersState();

  return (
    <div className="flex w-full max-w-full min-w-0 flex-col">
      <AnalysisFilterBar value={filters} onChange={setFilters} hideEntityFilter />
      <OpportunityContentDetailView
        subjectId={subjectId}
        filters={filters}
        promptId={promptId}
        platformsMeta={platformsMeta}
      />
    </div>
  );
}
