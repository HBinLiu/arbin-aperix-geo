import { useParams } from "react-router-dom";

import { AnalysisFilterBar } from "@/components/analysis/common/AnalysisFilterBar";
import { OpportunityBacklinkDetailView } from "@/components/opportunity/OpportunityBacklinkDetailView";
import { useAnalysisFiltersState } from "@/hooks/useAnalysisFiltersState";
import { useDashboardContext } from "@/hooks/useDashboardContext";

type BacklinkDetailPageProps = {
  subjectId: string;
};

function decodeRouteDomain(value: string | undefined): string {
  if (!value) return "";
  try {
    return decodeURIComponent(value).trim().toLowerCase();
  } catch {
    return value.trim().toLowerCase();
  }
}

/** 机会 · 引用信源 · 单域名详情 */
export function BacklinkDetailPage({ subjectId }: BacklinkDetailPageProps) {
  const { domain: domainParam } = useParams<{ domain: string }>();
  const domain = decodeRouteDomain(domainParam);
  const { subject } = useDashboardContext();
  const { filters, setFilters } = useAnalysisFiltersState();

  return (
    <div className="flex w-full max-w-full min-w-0 flex-col">
      <AnalysisFilterBar value={filters} onChange={setFilters} hideEntityFilter />
      <OpportunityBacklinkDetailView
        subjectId={subjectId}
        domain={domain}
        filters={filters}
        ownLabel={subject.brand}
        ownBrand={subject.brand}
      />
    </div>
  );
}
