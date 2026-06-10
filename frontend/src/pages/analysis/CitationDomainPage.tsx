import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { AnalysisFilterBar } from "@/components/analysis/common/AnalysisFilterBar";
import { CitationDomainDetailSection } from "@/components/analysis/citation/CitationDomainDetailSection";
import { CitationDomainSection } from "@/components/analysis/citation/CitationDomainSection";
import { useAnalysisOutletContext } from "@/hooks/useAnalysisContext";
import { useAnalysisFilter } from "@/hooks/useAnalysisFilter";
import { useCitationDomainAnalysis } from "@/hooks/useCitationDomainAnalysis";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { ANALYSIS_FILTER_ALL, DEFAULT_ANALYSIS_FILTERS } from "@/lib/analysis";
import type { AnalysisFilters } from "@/types";

function decodeRouteHost(value: string | undefined): string {
  if (!value) return "";
  try {
    return decodeURIComponent(value).trim().toLowerCase();
  } catch {
    return value.trim().toLowerCase();
  }
}

/** 分析 · 引用率 · 域名详情 */
export function CitationDomainPage() {
  const { host: hostParam } = useParams<{ host: string }>();
  const host = decodeRouteHost(hostParam);
  const { subjectId } = useAnalysisOutletContext();
  const { subject } = useDashboardContext();

  const [filters, setFilters] = useState<AnalysisFilters>(DEFAULT_ANALYSIS_FILTERS);

  useEffect(() => {
    setFilters((prev) => ({
      ...prev,
      regionId: ANALYSIS_FILTER_ALL,
      topicId: ANALYSIS_FILTER_ALL,
      platformId: ANALYSIS_FILTER_ALL,
    }));
  }, [subject.id]);

  const { isLoading, data } = useCitationDomainAnalysis(subjectId, host, filters);
  const { platforms: platformsMeta } = useAnalysisFilter();
  const ownLabel = subject.brand;

  return (
    <>
      <AnalysisFilterBar value={filters} onChange={setFilters} />

      <div className="flex flex-col gap-4 px-6 py-4">
        <CitationDomainSection data={data} loading={isLoading} />

        <CitationDomainDetailSection
          data={data}
          ownLabel={ownLabel}
          ownBrand={subject.brand}
          platformsMeta={platformsMeta}
          loading={isLoading}
        />
      </div>
    </>
  );
}
