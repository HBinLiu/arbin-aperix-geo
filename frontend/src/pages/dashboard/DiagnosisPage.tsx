import { useEffect, useMemo, useState } from "react";
import { Link2, MessagesSquare, TrendingDown } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { AnalysisFilterBar } from "@/components/analysis/common/AnalysisFilterBar";
import { DEFAULT_TABLE_PAGE_SIZE } from "@/components/analysis/common/TablePagination";
import { DiagnosisDimensionCard } from "@/components/diagnosis/DiagnosisDimensionCard";
import {
  DEFAULT_DIAGNOSIS_CONTENT_SORT,
  DiagnosisContentTable,
  type DiagnosisContentSortState,
} from "@/components/diagnosis/DiagnosisContentTable";
import { DiagnosisScoreGauge } from "@/components/diagnosis/DiagnosisScoreGauge";
import { useAnalysisFiltersState } from "@/hooks/useAnalysisFiltersState";
import { useDiagnosisContent } from "@/hooks/useDiagnosisContent";
import { useDiagnosisContentSummary } from "@/hooks/useDiagnosisContentSummary";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { diagnosisContentSortToApiField } from "@/lib/diagnosis/content";
import { diagnosisContentDetailPath } from "@/lib/diagnosis/nav";

type DiagnosisContentProps = {
  subjectId: string;
};

/** 诊断中心：得分概览、维度摘要与提示词诊断明细表 */
export function DiagnosisContent({ subjectId }: DiagnosisContentProps) {
  const { subject } = useDashboardContext();
  const { filters, setFilters } = useAnalysisFiltersState();
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);
  const [contentSort, setContentSort] = useState<DiagnosisContentSortState>(
    DEFAULT_DIAGNOSIS_CONTENT_SORT,
  );

  useEffect(() => {
    setPage(1);
    setContentSort(DEFAULT_DIAGNOSIS_CONTENT_SORT);
  }, [subject.id]);

  useEffect(() => {
    setPage(1);
  }, [filters, contentSort, pageSize]);

  const contentListRequest = useMemo(() => {
    const apiSort =
      contentSort.dir === "default"
        ? null
        : diagnosisContentSortToApiField(contentSort.column, contentSort.dir);
    return {
      page,
      pageSize,
      sortBy: apiSort?.sortBy ?? null,
      order: apiSort?.order,
    };
  }, [page, pageSize, contentSort]);

  const {
    isLoading: summaryLoading,
    overview,
  } = useDiagnosisContentSummary(subjectId, filters);

  const {
    loading: listLoading,
    fetching: listFetching,
    rows,
    total,
    page: currentPage,
    pageSize: currentPageSize,
  } = useDiagnosisContent(subjectId, filters, contentListRequest);

  return (
    <div className="flex w-full max-w-full min-w-0 flex-col">
      <AnalysisFilterBar value={filters} onChange={setFilters} hideEntityFilter />

      <div className="flex flex-col gap-4 px-4 py-4 sm:px-6">
        <div className="grid gap-4 xl:grid-cols-4">
          <DiagnosisScoreGauge
            className="xl:col-span-1"
            score={overview.overallScore}
            status={overview.overallStatus}
            loading={summaryLoading}
          />
          <div className="border-border flex min-h-[220px] min-w-0 flex-col divide-y divide-border overflow-hidden rounded-lg border bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04)] xl:col-span-3 xl:flex-row xl:divide-x xl:divide-y-0">
            <DiagnosisDimensionCard
              embedded
              title="AI 提及"
              description="当向 AI 提出相关问题时，品牌被提及的频率及其在回答中的排名。"
              icon={MessagesSquare}
              healthScore={overview.mention.health_score}
              priorityCounts={overview.mention.priority_counts}
              loading={summaryLoading}
            />
            <DiagnosisDimensionCard
              embedded
              title="品牌差距"
              description="在提及竞品的 AI 回答中你的品牌差距；直接反映了竞争对手在该话题下的统治力。"
              icon={TrendingDown}
              healthScore={overview.brandGap.health_score}
              priorityCounts={overview.brandGap.priority_counts}
              loading={summaryLoading}
            />
            <DiagnosisDimensionCard
              embedded
              title="来源差距"
              description="在竞品链接被引用的 AI 回答中你的网站差距，说明竞品的内容垄断了 AI 的参考信源。"
              icon={Link2}
              healthScore={overview.sourceGap.health_score}
              priorityCounts={overview.sourceGap.priority_counts}
              loading={summaryLoading}
            />
          </div>
        </div>

        <DiagnosisContentTable
          rows={rows}
          loading={listLoading}
          fetching={listFetching}
          total={total}
          page={currentPage}
          pageSize={currentPageSize}
          sort={contentSort}
          onSortChange={setContentSort}
          onPageChange={setPage}
          onPageSizeChange={setPageSize}
          onRowClick={(row) => {
            navigate(diagnosisContentDetailPath(row.promptId));
          }}
        />
      </div>
    </div>
  );
}
