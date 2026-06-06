import { useEffect, useState } from "react";

import { AnalysisFilterBar } from "@/components/analysis/common/AnalysisFilterBar";
import { BrandLeaderboardTable } from "@/components/rank/BrandLeaderboardTable";
import { useBrandRank } from "@/hooks/useBrandRank";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { ANALYSIS_FILTER_ALL, DEFAULT_ANALYSIS_FILTERS } from "@/lib/analysis";
import type { AnalysisFilters } from "@/types";

const PAGE_TITLE = "排行榜";
const PAGE_DESCRIPTION =
  "全景展示您相对于竞品的市场定位。通过监控周期性的表现波动，精准锁定值得深入研究和重点关注的关键竞争对手。";

type RankContentProps = {
  subjectId: string;
};

/** 排行榜：品牌竞品全指标对比。 */
export function RankContent({ subjectId }: RankContentProps) {
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

  const { isLoading, rows } = useBrandRank(subjectId, filters);

  return (
    <>
      <AnalysisFilterBar value={filters} onChange={setFilters} />

      <div className="flex flex-col gap-4 px-4 py-4 sm:px-6">
        <header>
          <h2 className="text-xl font-semibold tracking-tight">{PAGE_TITLE}</h2>
          <p className="text-muted-foreground mt-1 max-w-3xl text-sm leading-relaxed">
            {PAGE_DESCRIPTION}
          </p>
        </header>

        <BrandLeaderboardTable rows={rows} loading={isLoading} />
      </div>
    </>
  );
}
