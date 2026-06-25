import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import { AnalysisFilterBar } from "@/components/analysis/common/AnalysisFilterBar";
import { DEFAULT_TABLE_PAGE_SIZE } from "@/components/analysis/common/TablePagination";
import {
  DEFAULT_BACKLINK_OPPORTUNITY_SORT,
  OpportunityBacklinkTable,
  type BacklinkOpportunitySortState,
} from "@/components/opportunity/OpportunityBacklinkTable";
import { Input } from "@/components/ui/input";
import { useAnalysisFiltersState } from "@/hooks/useAnalysisFiltersState";
import { useBacklinkOpportunity } from "@/hooks/useBacklinkOpportunity";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { backlinkOpportunitySortToApiField } from "@/lib/opportunity/backlink";
import {
  BACKLINK_OPPORTUNITY_DESCRIPTION,
  BACKLINK_OPPORTUNITY_TITLE,
  SOCIAL_OPPORTUNITY_DESCRIPTION,
  SOCIAL_OPPORTUNITY_TITLE,
} from "@/lib/opportunity/meta";
import { backlinkOpportunityDetailPath, opportunityTabFromPathname } from "@/lib/opportunity/nav";
import type { OpportunityTab } from "@/types";

const TAB_META: Record<
  OpportunityTab,
  { title: string; description: string; empty: string; searchPlaceholder?: string }
> = {
  backlink: {
    title: BACKLINK_OPPORTUNITY_TITLE,
    description: BACKLINK_OPPORTUNITY_DESCRIPTION,
    empty: "暂无反向链接机会",
    searchPlaceholder: "搜索域名...",
  },
  social: {
    title: SOCIAL_OPPORTUNITY_TITLE,
    description: SOCIAL_OPPORTUNITY_DESCRIPTION,
    empty: "社交媒体机会即将推出",
  },
};

type OpportunityContentProps = {
  subjectId: string;
};

/** 机会页：反向链接 / 社交媒体 Tab */
export function OpportunityContent({ subjectId }: OpportunityContentProps) {
  const { subject } = useDashboardContext();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const activeTab = opportunityTabFromPathname(pathname);
  const { filters, setFilters } = useAnalysisFiltersState();
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_TABLE_PAGE_SIZE);
  const [backlinkSort, setBacklinkSort] = useState<BacklinkOpportunitySortState>(
    DEFAULT_BACKLINK_OPPORTUNITY_SORT,
  );

  useEffect(() => {
    setSearch("");
    setDebouncedSearch("");
    setPage(1);
    setBacklinkSort(DEFAULT_BACKLINK_OPPORTUNITY_SORT);
  }, [subject.id, activeTab]);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, filters, backlinkSort, pageSize]);

  const backlinkListRequest = useMemo(() => {
    const apiSort =
      backlinkSort.dir === "default"
        ? null
        : backlinkOpportunitySortToApiField(backlinkSort.column, backlinkSort.dir);
    return {
      page,
      pageSize,
      search: debouncedSearch,
      sortBy: apiSort?.sortBy ?? null,
      order: apiSort?.order,
    };
  }, [page, pageSize, debouncedSearch, backlinkSort]);

  const {
    loading: isBacklinkLoading,
    fetching: isBacklinkFetching,
    rows: backlinkRows,
    total: backlinkTotal,
    page: backlinkPage,
    pageSize: backlinkPageSize,
  } = useBacklinkOpportunity(
    subjectId,
    filters,
    backlinkListRequest,
    activeTab === "backlink",
  );
  const meta = TAB_META[activeTab];

  return (
    <div className="flex w-full max-w-full min-w-0 flex-col">
      <AnalysisFilterBar
        value={filters}
        onChange={setFilters}
        hideEntityFilter
        afterFilters={
          meta.searchPlaceholder ? (
            <div className="relative">
              <Search
                className="text-muted-foreground pointer-events-none absolute top-1/2 left-4 size-3.5 -translate-y-1/2"
                aria-hidden
              />
              <Input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder={meta.searchPlaceholder}
                controlSize="sm"
                className="border-border h-9 w-[min(100%,220px)] rounded-lg bg-white pr-3 pl-9 text-xs shadow-none"
                aria-label={meta.searchPlaceholder}
              />
            </div>
          ) : null
        }
      />

      <div className="flex flex-col gap-4 px-4 py-4 sm:px-6">
        <header>
          <h2 className="text-xl font-semibold tracking-tight">{meta.title}</h2>
          <p className="text-muted-foreground mt-1 max-w-4xl text-sm font-medium leading-relaxed">
            {meta.description}
          </p>
        </header>

        {activeTab === "backlink" ? (
          <OpportunityBacklinkTable
            rows={backlinkRows}
            loading={isBacklinkLoading}
            fetching={isBacklinkFetching}
            total={backlinkTotal}
            page={backlinkPage}
            pageSize={backlinkPageSize}
            sort={backlinkSort}
            onSortChange={setBacklinkSort}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
            onRowClick={(row) => {
              navigate(backlinkOpportunityDetailPath(row.domain));
            }}
          />
        ) : (
          <div className="border-border text-muted-foreground flex min-h-[240px] items-center justify-center rounded-lg border bg-white px-6 py-10 text-sm">
            {meta.empty}
          </div>
        )}
      </div>
    </div>
  );
}
