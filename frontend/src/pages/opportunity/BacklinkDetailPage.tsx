import { useParams } from "react-router-dom";

import { AnalysisFilterBar } from "@/components/analysis/common/AnalysisFilterBar";
import { OpportunityBacklinkDetailView } from "@/components/opportunity/OpportunityBacklinkDetailView";
import { useAnalysisFilter } from "@/hooks/useAnalysisFilter";
import { useAnalysisFiltersState } from "@/hooks/useAnalysisFiltersState";
import { useDashboardContext } from "@/hooks/useDashboardContext";

type BacklinkDetailPageProps = {
  subjectId: string;
};

function decodeRouteHost(value: string | undefined): string {
  if (!value) return "";
  try {
    return decodeURIComponent(value).trim().toLowerCase();
  } catch {
    return value.trim().toLowerCase();
  }
}

/** 机会 · 反向链接 · 单域名详情 */
export function BacklinkDetailPage({ subjectId }: BacklinkDetailPageProps) {
  const { host: hostParam } = useParams<{ host: string }>();
  const host = decodeRouteHost(hostParam);
  const { subject } = useDashboardContext();
  const { platforms: platformsMeta } = useAnalysisFilter();
  const { filters, setFilters } = useAnalysisFiltersState();

  return (
    <div className="flex w-full max-w-full min-w-0 flex-col">
      <AnalysisFilterBar value={filters} onChange={setFilters} hideEntityFilter />
      <OpportunityBacklinkDetailView
        subjectId={subjectId}
        host={host}
        filters={filters}
        ownLabel={subject.brand}
        ownBrand={subject.brand}
        platformsMeta={platformsMeta}
      />
    </div>
  );
}
