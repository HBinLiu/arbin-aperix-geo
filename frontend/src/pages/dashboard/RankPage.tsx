import { AnalysisFilterBar } from "@/components/analysis/common/AnalysisFilterBar";
import { RankBoardTable } from "@/components/rank/RankBoardTable";
import { useAnalysisFiltersState } from "@/hooks/useAnalysisFiltersState";
import { useRankBoardData } from "@/hooks/useRankBoardData";

const PAGE_TITLE = "排行榜";
const PAGE_DESCRIPTION =
  "全景展示您相对于竞品的市场定位。通过监控周期性的表现波动，精准锁定值得深入研究和重点关注的关键竞争对手。";

type RankContentProps = {
  subjectId: string;
};

/** 排行榜：品牌竞品全指标对比。 */
export function RankContent({ subjectId }: RankContentProps) {
  const { filters, setFilters } = useAnalysisFiltersState();

  const { isLoading, rows } = useRankBoardData(subjectId, filters);

  return (
    <>
      <AnalysisFilterBar value={filters} onChange={setFilters} hideEntityFilter />

      <div className="flex flex-col gap-4 px-4 py-4 sm:px-6">
        <header>
          <h2 className="text-xl font-semibold tracking-tight">{PAGE_TITLE}</h2>
          <p className="text-muted-foreground mt-1 max-w-3xl text-sm leading-relaxed">
            {PAGE_DESCRIPTION}
          </p>
        </header>

        <RankBoardTable rows={rows} loading={isLoading} />
      </div>
    </>
  );
}
