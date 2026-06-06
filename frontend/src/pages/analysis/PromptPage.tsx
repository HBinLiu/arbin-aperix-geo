import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Search, Settings2 } from "lucide-react";

import { AnalysisFilterBar } from "@/components/analysis/common/AnalysisFilterBar";
import { PromptPerformanceTable } from "@/components/analysis/prompt/PromptPerformanceTable";
import { TopicPerformanceTable } from "@/components/analysis/prompt/TopicPerformanceTable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAnalysisOutletContext } from "@/hooks/useAnalysisContext";
import { filterPromptRowsBySearch, usePromptAnalysis } from "@/hooks/usePromptAnalysis";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { ANALYSIS_FILTER_ALL, DEFAULT_ANALYSIS_FILTERS } from "@/lib/analysis";
import { dashboardNavToPath } from "@/lib/dashboard";
import type { AnalysisFilters } from "@/types";

const PAGE_TITLE = "提示词表现";
const PAGE_DESCRIPTION =
  "在提示词层面分析产品可见度与表现，帮助理解 AI 搜索场景下的用户需求与转化潜力。";

/** 分析 · 提示词表现 */
export function PromptPage() {
  const { subjectId } = useAnalysisOutletContext();
  const { subject } = useDashboardContext();
  const [filters, setFilters] = useState<AnalysisFilters>(DEFAULT_ANALYSIS_FILTERS);
  const [search, setSearch] = useState("");

  useEffect(() => {
    setFilters((prev) => ({
      ...prev,
      regionId: ANALYSIS_FILTER_ALL,
      topicId: ANALYSIS_FILTER_ALL,
      platformId: ANALYSIS_FILTER_ALL,
    }));
    setSearch("");
  }, [subject.id]);

  const { isLoading, topicRows, promptRows } = usePromptAnalysis(subjectId, filters);

  const filteredPromptRows = useMemo(
    () => filterPromptRowsBySearch(promptRows, search),
    [promptRows, search],
  );

  return (
    <div className="flex w-full max-w-full min-w-0 flex-col">
      <AnalysisFilterBar
        value={filters}
        onChange={setFilters}
        afterFilters={
          <div className="relative">
            <Search
              className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-3.5 -translate-y-1/2"
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
          <Button variant="default" size="sm" className="h-9 rounded-lg px-3 text-xs" asChild>
            <Link to={dashboardNavToPath("brand")}>
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

        <TopicPerformanceTable rows={topicRows} loading={isLoading} />
        <PromptPerformanceTable rows={filteredPromptRows} loading={isLoading} />
      </div>
    </div>
  );
}
