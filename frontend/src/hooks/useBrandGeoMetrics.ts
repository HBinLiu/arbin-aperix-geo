import { useMemo } from "react";

import { useAnalysisFiltersState } from "@/hooks/useAnalysisFiltersState";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { useRankBoardData } from "@/hooks/useRankBoardData";
import {
  brandGeoMetricsFromRankItems,
  EMPTY_BRAND_GEO_METRICS,
  type BrandGeoMetrics,
} from "@/lib/brand/geoMetrics";
import type { CompetitorItem } from "@/types";

/** 悬停卡 GEO 四指标：复用 /rank 与当前 FilterBar 筛选。 */
export function useBrandGeoMetrics(
  row: CompetitorItem,
  override?: BrandGeoMetrics,
): { metrics: BrandGeoMetrics; isLoading: boolean } {
  const { subject } = useDashboardContext();
  const { filters } = useAnalysisFiltersState();
  const { data, isLoading } = useRankBoardData(subject.id, filters);

  const metrics = useMemo(() => {
    if (override) return override;
    if (!data?.items.length) return EMPTY_BRAND_GEO_METRICS;
    return brandGeoMetricsFromRankItems(data.items, row);
  }, [override, data?.items, row.brand, row.domain, row.aliases]);

  return {
    metrics,
    isLoading: override ? false : isLoading,
  };
}
