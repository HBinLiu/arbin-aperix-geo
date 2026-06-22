import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Search, Settings2 } from "lucide-react";

import { AnalysisFilterBar } from "@/components/analysis/common/AnalysisFilterBar";
import {
  DEFAULT_TABLE_PAGE_SIZE,
} from "@/components/analysis/common/TablePagination";
import { PromptPerformanceTable } from "@/components/analysis/prompt/PromptPerformanceTable";
import { TopicPerformanceTable } from "@/components/analysis/prompt/TopicPerformanceTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAnalysisOutletContext } from "@/hooks/useAnalysisContext";
import { useAnalysisFiltersState } from "@/hooks/useAnalysisFiltersState";
import { usePromptAnalysis } from "@/hooks/usePromptAnalysis";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { dashboardNavToPath } from "@/lib/dashboard";
import { promptSortToApiField } from "@/lib/analysis/prompt";

const PAGE_TITLE = "提示词表现";
const PAGE_DESCRIPTION =
  "在提示词层面分析产品可见度与表现，帮助理解 AI 搜索场景下的用户需求与转化潜力。";

type PromptTableSortKey = "visibility" | "sentiment" | "averageRank" | "citationRate";
type PromptTableSortDir = "asc" | "desc";
type PromptTableSortState = { key: PromptTableSortKey; dir: PromptTableSortDir } | null;

/** 分析 · 提示词表现 */
export function PromptPage() {
  const { subjectId } = useAnalysisOutletContext();
  const { subject } = useDashboardContext();
  const { filters, setFilters } = useAnalysisFiltersState();
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [selectedTopicId, setSelectedTopicId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);
  const [sort, setSort] = useState<PromptTableSortState>(null);

  useEffect(() => {
    setSearch("");
    setDebouncedSearch("");
    setSelectedTopicId(null);
    setPage(1);
    setSort(null);
  }, [subject.id]);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, selectedTopicId, filters, sort, pageSize]);

  const listRequest = useMemo(
    () => ({
      page,
      pageSize,
      search: debouncedSearch,
      topicId: selectedTopicId,
      sortBy: promptSortToApiField(sort?.key),
      order: sort?.dir ?? "desc",
    }),
    [page, pageSize, debouncedSearch, selectedTopicId, sort],
  );

  const { topicsLoading, promptsLoading, promptsFetching, topicRows, promptRows, promptTotal } = usePromptAnalysis(
    subjectId,
    filters,
    listRequest,
  );

  return (
    <div className="flex w-full max-w-full min-w-0 flex-col">
      <AnalysisFilterBar
        value={filters}
        onChange={setFilters}
        afterFilters={
          <div className="relative">
            <Search
              className="text-muted-foreground pointer-events-none absolute top-1/2 left-4 size-3.5 -translate-y-1/2"
              aria-hidden
            />
            <Input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="搜索提示词"
              controlSize="sm"
              className="border-border h-9 w-[min(100%,220px)] rounded-lg bg-white pr-3 pl-9 text-xs shadow-none"
              aria-label="搜索提示词"
            />
          </div>
        }
        trailing={
          <Button variant="brandout" size="sm" className="h-9 rounded-lg px-3 font-medium text-sm" asChild>
            <Link to={dashboardNavToPath("prompt")}>
              <Settings2 className="size-3.5" aria-hidden />
              管理提示词
            </Link>
          </Button>
        }
      />

      <div className="flex w-full max-w-full min-w-0 flex-col gap-4 px-6 py-4">
        <header>
          <h2 className="text-xl font-semibold tracking-tight">{PAGE_TITLE}</h2>
          <p className="text-muted-foreground mt-1 max-w-3xl text-sm leading-relaxed">
            {PAGE_DESCRIPTION}
          </p>
        </header>

        <TopicPerformanceTable
          rows={topicRows}
          selectedTopicId={selectedTopicId}
          onTopicSelect={setSelectedTopicId}
          loading={topicsLoading}
        />
        <PromptPerformanceTable
          rows={promptRows}
          loading={promptsLoading}
          fetching={promptsFetching}
          total={promptTotal}
          page={page}
          pageSize={pageSize}
          sort={sort}
          onSortChange={setSort}
          onPageChange={setPage}
          onPageSizeChange={setPageSize}
        />
      </div>
    </div>
  );
}
