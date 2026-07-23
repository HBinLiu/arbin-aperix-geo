import { useEffect, useState } from "react";
import { Search } from "lucide-react";

import { AnalysisFilterBar } from "@/components/analysis/common/AnalysisFilterBar";
import { DEFAULT_TABLE_PAGE_SIZE } from "@/components/analysis/common/TablePagination";
import { FanoutOverviewSection } from "@/components/analysis/fanout/FanoutOverviewSection";
import {
  FanoutPromptTable,
  type FanoutPromptSortState,
} from "@/components/analysis/fanout/FanoutPromptTable";
import { Input } from "@/components/ui/input";
import { useAnalysisOutletContext } from "@/hooks/useAnalysisContext";
import { useAnalysisFiltersState } from "@/hooks/useAnalysisFiltersState";
import { useFanoutAnalysis, useFanoutPrompts } from "@/hooks/useFanoutAnalysis";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { ANALYSIS_DIMENSIONS } from "@/lib/analysis";

const FANOUT_META = ANALYSIS_DIMENSIONS.find((d) => d.id === "fanout")!;

/** 分析 · 查询扇出 */
export function FanoutPage() {
  const { subjectId } = useAnalysisOutletContext();
  const { subject } = useDashboardContext();
  const { filters, setFilters } = useAnalysisFiltersState();
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);
  const [sort, setSort] = useState<FanoutPromptSortState>({ key: "quantity", dir: "desc" });

  useEffect(() => {
    setSearch("");
    setDebouncedSearch("");
    setPage(1);
    setSort({ key: "quantity", dir: "desc" });
  }, [subject.id]);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, filters, sort, pageSize]);

  const { isLoading, overview } = useFanoutAnalysis(subjectId, filters);
  const { isLoading: promptsLoading, isFetching, rows, total } = useFanoutPrompts(
    subjectId,
    filters,
    {
      page,
      pageSize,
      sortBy: sort?.key ?? "quantity",
      order: sort?.dir ?? "desc",
      search: debouncedSearch,
    },
  );

  return (
    <>
      <AnalysisFilterBar
        value={filters}
        onChange={setFilters}
        afterFilters={
          <div className="relative w-[min(100%,240px)]">
            <span className="pointer-events-none absolute inset-y-0 left-3.5 z-10 flex items-center">
              <Search className="text-muted-foreground size-3.5" aria-hidden />
            </span>
            <Input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="搜索提示词"
              controlSize="sm"
              className="border-border h-9 w-full rounded-lg bg-muted-background pl-9 text-xs"
              aria-label="搜索提示词"
            />
          </div>
        }
      />

      <div className="flex flex-col gap-4 px-6 py-4">
        <header>
          <h2 className="text-xl font-semibold tracking-tight">查询扇出分析</h2>
          <p className="text-muted-foreground mt-1 max-w-4xl text-sm leading-relaxed">
            {FANOUT_META.description}
          </p>
        </header>

        <FanoutOverviewSection
          overview={overview}
          subjectScopeKey={`${subjectId}:fanout`}
          loading={isLoading}
        />

        <FanoutPromptTable
          rows={rows}
          chartLabels={overview.chartLabels}
          loading={promptsLoading}
          fetching={isFetching && !promptsLoading}
          total={total}
          page={page}
          pageSize={pageSize}
          sort={sort}
          onSortChange={setSort}
          onPageChange={setPage}
          onPageSizeChange={setPageSize}
        />
      </div>
    </>
  );
}
