import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { useLocation } from "react-router-dom";

import { AnalysisFilterBar } from "@/components/analysis/common/AnalysisFilterBar";
import { OpportunityBacklinkTable } from "@/components/opportunity/OpportunityBacklinkTable";
import { OpportunityContentTable } from "@/components/opportunity/OpportunityContentTable";
import { Input } from "@/components/ui/input";
import { useAnalysisFilter } from "@/hooks/useAnalysisFilter";
import { useBacklinkOpportunity } from "@/hooks/useBacklinkOpportunity";
import { useContentOpportunity } from "@/hooks/useContentOpportunity";
import { useDashboardContext } from "@/hooks/useDashboardContext";
import { ANALYSIS_FILTER_ALL, DEFAULT_ANALYSIS_FILTERS } from "@/lib/analysis";
import {
  BACKLINK_OPPORTUNITY_DESCRIPTION,
  BACKLINK_OPPORTUNITY_TITLE,
  CONTENT_OPPORTUNITY_DESCRIPTION,
  CONTENT_OPPORTUNITY_TITLE,
  SOCIAL_OPPORTUNITY_DESCRIPTION,
  SOCIAL_OPPORTUNITY_TITLE,
} from "@/lib/opportunity/content";
import { opportunityTabFromPathname } from "@/lib/opportunity/nav";
import type { AnalysisFilters, OpportunityTab } from "@/types";

const TAB_META: Record<
  OpportunityTab,
  { title: string; description: string; empty: string; searchPlaceholder?: string }
> = {
  content: {
    title: CONTENT_OPPORTUNITY_TITLE,
    description: CONTENT_OPPORTUNITY_DESCRIPTION,
    empty: "暂无内容机会",
    searchPlaceholder: "搜索提示词...",
  },
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

/** 机会页：内容 / 反向链接 / 社交媒体 Tab */
export function OpportunityContent({ subjectId }: OpportunityContentProps) {
  const { subject } = useDashboardContext();
  const { platforms } = useAnalysisFilter();
  const { pathname } = useLocation();
  const activeTab = opportunityTabFromPathname(pathname);
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
  }, [subject.id, activeTab]);

  const { isLoading: isContentLoading, rows: contentRows } = useContentOpportunity(
    subjectId,
    filters,
    search,
    activeTab === "content",
  );
  const { isLoading: isBacklinkLoading, rows: backlinkRows } = useBacklinkOpportunity(
    subjectId,
    filters,
    search,
    activeTab === "backlink",
  );
  const meta = TAB_META[activeTab];

  return (
    <div className="flex w-full max-w-full min-w-0 flex-col">
      <AnalysisFilterBar
        value={filters}
        onChange={setFilters}
        afterFilters={
          meta.searchPlaceholder ? (
            <div className="relative">
              <Search
                className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-3.5 -translate-y-1/2"
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
          <p className="text-muted-foreground mt-1 max-w-3xl text-sm leading-relaxed">
            {meta.description}
          </p>
        </header>

        {activeTab === "content" ? (
          <OpportunityContentTable rows={contentRows} platformsMeta={platforms} loading={isContentLoading} />
        ) : activeTab === "backlink" ? (
          <OpportunityBacklinkTable rows={backlinkRows} platformsMeta={platforms} loading={isBacklinkLoading} />
        ) : (
          <div className="border-border text-muted-foreground flex min-h-[240px] items-center justify-center rounded-lg border bg-white px-6 py-10 text-sm">
            {meta.empty}
          </div>
        )}
      </div>
    </div>
  );
}
